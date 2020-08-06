# -*- coding: utf-8 -*-
# This file is part of Shuup Stripe Addon.
#
# Copyright (c) 2012-2018, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
import mock
import pytest
import stripe
from django.urls import reverse
from shuup.core import cache
from shuup.core.models import get_person_contact
from shuup.front.views.dashboard import DashboardView
from shuup.testing import factories
from shuup.testing.utils import apply_request_middleware

from shuup_stripe.models import StripeCheckoutPaymentProcessor, StripeCustomer
from shuup_stripe.utils import set_saved_card_message
from shuup_stripe.views import (
    StripeDeleteSavedPaymentInfoView, StripeSavedPaymentInfoView
)

CUSTOMER_MOCK_DATA = {
    "id": "cus_cxu8u832hd23897gh29",
    "sources": {
        "data": [
            {
                "id": "card_xpdu3892dh279g7a",
                "object": "card",
                "brand": "Visa",
                "funding": "credit",
                "last4": "5555",
                "exp_month": "1",
                "exp_year": "2080"
            }
        ]
    }
}


class StripedData(dict):
    def __getattr__(self, attr):
        return self[attr]

    def json(self):
        return self


class StripeCustomerData(StripedData):
    def to_dict(self):
        return self


@pytest.fixture
def stripe_payment_processor():
    return StripeCheckoutPaymentProcessor.objects.create(secret_key="secret", publishable_key="x")


@pytest.mark.django_db
def test_save_card(rf, stripe_payment_processor):
    cache.clear()
    shop = factories.get_default_shop()
    user = factories.create_random_user()
    contact = get_person_contact(user)
    view = StripeSavedPaymentInfoView.as_view()

    # retrieve the saved card view
    request = apply_request_middleware(rf.get("/"), customer=contact, shop=shop, user=user)
    response = view(request)
    assert response.status_code == 200
    response.render()
    content = response.content.decode("utf-8")
    assert "Save your card details for a faster checkout. You can change or delete it at any time." in content

    set_saved_card_message(shop, "ABC1234")
    response = view(request)
    response.render()
    content = response.content.decode("utf-8")
    assert "Save your card details for a faster checkout. You can change or delete it at any time." not in content
    assert "ABC1234" in content

    def return_stripe_mock_data(*args, **kwargs):
        return StripeCustomerData(**CUSTOMER_MOCK_DATA)

    with mock.patch("stripe.Customer.retrieve", new=return_stripe_mock_data):
        with mock.patch("stripe.Customer.modify", new=return_stripe_mock_data):
            with mock.patch("stripe.Customer.create", new=return_stripe_mock_data):
                # attach payment details
                request = apply_request_middleware(rf.post("/", {
                    "stripeToken": "xpto"
                }), customer=contact, shop=shop, user=user)
                response = view(request)
                assert response.status_code == 302
                assert response.url.endswith(reverse("shuup:stripe_saved_payment"))

                # make sure there is stripe customer
                assert StripeCustomer.objects.filter(contact=contact, customer_token=CUSTOMER_MOCK_DATA["id"]).exists()

                # retrieve info
                request = apply_request_middleware(rf.get("/"), customer=contact, shop=shop, user=user)
                response = view(request)
                assert response.status_code == 200
                response.render()
                content = response.content.decode("utf-8")
                assert "Expires" in content
                assert CUSTOMER_MOCK_DATA["sources"]["data"][0]["id"] in content

                # "change" attach payment details
                request = apply_request_middleware(rf.post("/", {
                    "stripeToken": "xpto234"
                }), customer=contact, shop=shop, user=user)
                response = view(request)
                assert response.status_code == 302
                assert response.url.endswith(reverse("shuup:stripe_saved_payment"))

    def raise_stripe_exc(*args, **kwargs):
        raise stripe.error.StripeError("DUMMY")

    # raise when fetching customer
    with mock.patch("stripe.Customer.retrieve", new=raise_stripe_exc):
        request = apply_request_middleware(rf.get("/"), customer=contact, shop=shop, user=user)
        response = view(request)
        assert response.status_code == 200
        response.render()
        content = response.content.decode("utf-8")
        assert "Expires" not in content

    StripeCustomer.objects.all().delete()

    # now raise exception when saving new payment detail
    with mock.patch("stripe.Customer.retrieve", new=return_stripe_mock_data):
        with mock.patch("stripe.Customer.create", new=raise_stripe_exc):
            request = apply_request_middleware(rf.post("/", {
                "stripeToken": "xpto3"
            }), customer=contact, shop=shop, user=user)
            response = view(request)
            assert response.status_code == 302
            assert response.url.endswith(reverse("shuup:stripe_saved_payment"))

            # error, nothing created
            assert not StripeCustomer.objects.exists()

    cache.clear()


@pytest.mark.django_db
def test_delete_saved_card(rf, stripe_payment_processor):
    shop = factories.get_default_shop()
    user = factories.create_random_user()
    contact = get_person_contact(user)
    view = StripeSavedPaymentInfoView.as_view()
    delete_view = StripeDeleteSavedPaymentInfoView.as_view()

    # retrieve the saved card view
    request = apply_request_middleware(rf.get("/"), customer=contact, shop=shop, user=user)
    response = view(request)
    assert response.status_code == 200
    response.render()
    content = response.content.decode("utf-8")
    assert "Save your card details for a faster checkout. You can change or delete it at any time." in content

    def return_stripe_mock_data(*args, **kwargs):
        return StripeCustomerData(**CUSTOMER_MOCK_DATA)

    with mock.patch("stripe.Customer.retrieve", new=return_stripe_mock_data):
        with mock.patch("stripe.Customer.modify", new=return_stripe_mock_data):
            with mock.patch("stripe.Customer.create", new=return_stripe_mock_data):
                # attach payment details
                request = apply_request_middleware(rf.post("/", {
                    "stripeToken": "xpto"
                }), customer=contact, shop=shop, user=user)
                response = view(request)
                assert response.status_code == 302
                assert response.url.endswith(reverse("shuup:stripe_saved_payment"))

                # make sure there is stripe customer
                assert StripeCustomer.objects.filter(contact=contact, customer_token=CUSTOMER_MOCK_DATA["id"]).exists()

    def get_delete_mock():
        mock_for_delete = mock.Mock(wraps=StripeCustomerData(**CUSTOMER_MOCK_DATA))
        mock_for_delete.sources = mock.Mock()
        mock_for_delete.sources.retrieve = mock.Mock()
        return mock_for_delete

    with mock.patch("stripe.Customer.retrieve") as mocked:
        mock_for_delete = get_delete_mock()
        mocked.return_value = mock_for_delete

        # Delete the source
        request = apply_request_middleware(rf.post("/", {
            "source_id": CUSTOMER_MOCK_DATA["sources"]["data"][0]["id"]
        }), customer=contact, shop=shop, user=user)
        response = delete_view(request)

        mock_for_delete.sources.retrieve.delete.asset_called()

        # delete with error
        mock_for_delete = get_delete_mock()
        mock_for_delete.sources.retrieve.side_effect = stripe.error.StripeError("dummy")
        mocked.return_value = mock_for_delete
        response = delete_view(request)
        mock_for_delete.sources.retrieve.delete.asset_called()


@pytest.mark.django_db
def test_dashboard_item(rf):
    shop = factories.get_default_shop()
    user = factories.create_random_user()
    contact = get_person_contact(user)
    view = DashboardView.as_view()

    request = apply_request_middleware(rf.get("/"), customer=contact, shop=shop, user=user)
    response = view(request)
    assert response.status_code == 200
    response.render()
    content = response.content.decode("utf-8")
    assert "Saved Card" in content
