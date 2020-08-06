# -*- coding: utf-8 -*-
# This file is part of Shuup Stripe Addon.
#
# Copyright (c) 2012-2018, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
import mock
import pytest
from django.urls import reverse
from shuup.front.basket import get_basket
from shuup.testing.factories import get_default_shop, get_default_tax_class
from shuup.testing.utils import apply_request_middleware
from shuup.utils.excs import Problem

from shuup_stripe.checkout_phase import StripeCheckoutPhase
from shuup_stripe.models import StripeCheckoutPaymentProcessor

from .utils import create_order_for_stripe, get_stripe_token


class StripedData(dict):
    def __getattr__(self, attr):
        return self[attr]

    def json(self):
        return self


@pytest.fixture
def stripe_payment_processor():
    return StripeCheckoutPaymentProcessor.objects.create(secret_key="secret", publishable_key="x")


@pytest.mark.django_db
def test_stripe_basics(rf, stripe_payment_processor):
    """
    :type rf: RequestFactory
    :type stripe_payment_module: StripeCheckoutModule
    """
    with mock.patch("shuup.utils.http.retry_request") as mocked:
        mocked.return_value = StripedData(paid=True, id="1234")

        order = create_order_for_stripe(stripe_payment_processor)
        token = get_stripe_token(stripe_payment_processor)
        token_id = token["id"]
        order.payment_data["stripe"] = {"token": token_id}
        order.save()
        service = order.payment_method
        stripe_payment_processor.process_payment_return_request(
            service, order, rf.post("/"))
        assert order.is_paid()
        assert order.payments.first().payment_identifier.startswith("Stripe-")


@pytest.mark.django_db
def test_stripe_bogus_data_fails(rf, stripe_payment_processor):
    with mock.patch("shuup.utils.http.retry_request") as mocked:
        mocked.return_value = StripedData()

        order = create_order_for_stripe(stripe_payment_processor)
        with pytest.raises(Problem):
            stripe_payment_processor.process_payment_return_request(order.payment_method, order, rf.post("/"))

    with mock.patch("shuup.utils.http.retry_request") as mocked:
        mocked.return_value = StripedData(error=dict(type="error1", message="failed"))

        order = create_order_for_stripe(stripe_payment_processor)
        with pytest.raises(Problem):
            stripe_payment_processor.process_payment_return_request(order.payment_method, order, rf.post("/"))

    with mock.patch("shuup.utils.http.retry_request") as mocked:
        mocked.return_value = StripedData(failure_message="failed", failure_code="0xf2")
        order = create_order_for_stripe(stripe_payment_processor)
        with pytest.raises(Problem):
            stripe_payment_processor.process_payment_return_request(order.payment_method, order, rf.post("/"))


@pytest.mark.django_db
def test_stripe_checkout_phase(rf):
    request = apply_request_middleware(rf.post("/"), shop=get_default_shop())
    request.session = {}
    request.basket = get_basket(request)

    payment_processor = StripeCheckoutPaymentProcessor.objects.create(secret_key="secret", publishable_key="12", name="Stripe")
    service = payment_processor.create_service("stripe", shop=request.shop, tax_class=get_default_tax_class(), enabled=True)
    checkout_phase = StripeCheckoutPhase(request=request, service=service)
    assert not checkout_phase.is_valid()  # We can't be valid just yet
    context = checkout_phase.get_context_data()
    assert context["stripe"]
    request.method = "POST"
    request.POST = {
        "stripeToken": "1234",
        "stripeTokenType": "12442",
        "stripeTokenEmail": "4212342",
    }
    checkout_phase.get_success_url = lambda: reverse("shuup_admin:home")
    checkout_phase.post(request)
    assert checkout_phase.is_valid()  # We should be valid now
    assert request.session  # And things should've been saved into the session
    checkout_phase.process()  # And this should do things to the basket
    assert request.basket.payment_data.get("stripe")


@pytest.mark.django_db
def test_stripe_process_order(rf):
    with mock.patch("shuup.utils.http.retry_request") as mocked:
        mocked.return_value = StripedData(paid=True, id="1234")

        request = rf.post("/")
        shop = get_default_shop()
        payment_processor = StripeCheckoutPaymentProcessor.objects.create(secret_key="secret", publishable_key="12")
        service = payment_processor.create_service("stripe", shop=shop, tax_class=get_default_tax_class(), enabled=True)
        order = create_order_for_stripe(payment_processor)
        payment_processor.process_payment_return_request(service, order, request)

    mocked.assert_called_once()


@pytest.mark.django_db
def test_stripe_checkout_phase_mocked(rf):
    shop = get_default_shop()
    request = apply_request_middleware(rf.post("/"))
    payment_processor = StripeCheckoutPaymentProcessor.objects.create(secret_key="secret", publishable_key="12", name="Stripe")
    service = payment_processor.create_service("stripe", shop=shop, tax_class=get_default_tax_class(), enabled=True, name="Stripe", description="desc")
    checkout_phase = StripeCheckoutPhase(request=request, service=service)
    stripe_context = checkout_phase.get_stripe_context()
    assert stripe_context["publishable_key"] == payment_processor.publishable_key
    assert stripe_context["name"] == shop.name
    assert stripe_context["description"] == "Purchase"

    assert not checkout_phase.is_valid()


@pytest.mark.django_db
def test_stripe_checkout_phase_with_misconfigured_module(rf):
    payment_processor = StripeCheckoutPaymentProcessor.objects.create()
    request = apply_request_middleware(rf.get("/"), shop=get_default_shop())
    request.session = {}
    request.basket = get_basket(request)
    service = payment_processor.create_service("stripe", shop=request.shop, tax_class=get_default_tax_class(), enabled=True)
    checkout_phase = StripeCheckoutPhase(request=request, service=service)

    with pytest.raises(Problem):
        checkout_phase.get_context_data()
