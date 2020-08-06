# -*- coding: utf-8 -*-
# This file is part of Shuup Stripe Addon.
#
# Copyright (c) 2012-2018, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
import os

import mock
import pytest
import stripe
from django.urls import reverse
from shuup.core.models import get_person_contact
from shuup.front.basket import get_basket
from shuup.testing import factories
from shuup.testing.utils import apply_request_middleware
from shuup.utils.excs import Problem

from shuup_stripe.checkout_phase import StripeCheckoutPhase
from shuup_stripe.models import StripeCheckoutPaymentProcessor, StripeCustomer

from .utils import create_order_for_stripe, get_stripe_token

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

    def to_dict(self):
        return self


@pytest.fixture
def stripe_payment_processor():
    return StripeCheckoutPaymentProcessor.objects.create(secret_key="secret", publishable_key="x")


@pytest.mark.django_db
def test_stripe_basics_with_saved_card(rf, stripe_payment_processor):
    """
    :type rf: RequestFactory
    :type stripe_payment_module: StripeCheckoutModule
    """
    with mock.patch("shuup.utils.http.retry_request") as mocked:
        mocked.return_value = StripedData(paid=True, id="1234")
        order = create_order_for_stripe(stripe_payment_processor)
        order.payment_data["stripe"] = {"customer": "cus_dj283ud823u8"}
        order.save()
        service = order.payment_method
        stripe_payment_processor.process_payment_return_request(
            service, order, rf.post("/"))
        assert order.is_paid()
        assert order.payments.first().payment_identifier.startswith("Stripe-")


@pytest.mark.django_db
def test_stripe_checkout_phase_with_saved_card(rf, stripe_payment_processor):
    shop = factories.get_default_shop()
    user = factories.create_random_user()
    contact = get_person_contact(user)
    request = apply_request_middleware(rf.post("/"), shop=shop, customer=contact)

    def return_stripe_mock_data(*args, **kwargs):
        return StripedData(**CUSTOMER_MOCK_DATA)

    with mock.patch("stripe.Customer.retrieve", new=return_stripe_mock_data):
        service = stripe_payment_processor.create_service(
            "stripe", shop=request.shop, tax_class=factories.get_default_tax_class(), enabled=True)

        StripeCustomer.objects.create(contact=contact, customer_token="123")
        checkout_phase = StripeCheckoutPhase(request=request, service=service)
        assert not checkout_phase.is_valid()
        context = checkout_phase.get_context_data()
        assert context["stripe"]
        request.method = "POST"
        request.POST = {
            "stripeCustomer": "1234"
        }
        checkout_phase.get_success_url = lambda: reverse("shuup_admin:home")
        checkout_phase.post(request)
        assert checkout_phase.is_valid()  # We should be valid now
        assert request.session  # And things should've been saved into the session
        checkout_phase.process()  # And this should do things to the basket
        assert request.basket.payment_data["stripe"]["customer"]



@pytest.mark.django_db
def test_stripe_checkout_phase_with_saved_card_exception(rf, stripe_payment_processor):
    shop = factories.get_default_shop()
    user = factories.create_random_user()
    contact = get_person_contact(user)
    request = apply_request_middleware(rf.post("/"), shop=shop, customer=contact)

    def raise_stripe_exc(*args, **kwargs):
        raise stripe.error.StripeError("DUMMY")

    with mock.patch("stripe.Customer.retrieve", new=raise_stripe_exc):
        service = stripe_payment_processor.create_service(
            "stripe", shop=request.shop, tax_class=factories.get_default_tax_class(), enabled=True)

        StripeCustomer.objects.create(contact=contact, customer_token="123")
        checkout_phase = StripeCheckoutPhase(request=request, service=service)
        assert not checkout_phase.is_valid()
        context = checkout_phase.get_context_data()
        assert context["stripe"]
        assert not context.get("stripe_customer_data")

        request.method = "POST"
        request.POST = {}
        checkout_phase.get_success_url = lambda: reverse("shuup_admin:home")
        checkout_phase.post(request)
        assert not checkout_phase.is_valid()
