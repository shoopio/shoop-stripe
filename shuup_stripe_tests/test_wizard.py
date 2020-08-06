# -*- coding: utf-8 -*-
# This file is part of Shuup Stripe Addon.
#
# Copyright (c) 2012-2018, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
import mock
import pytest
from django.conf import settings
from django.test import override_settings
from django.test.client import Client
from django.urls import reverse
from shuup.admin.shop_provider import SHOP_SESSION_KEY
from shuup.admin.views.wizard import WizardView
from shuup.testing import factories
from shuup.testing.utils import apply_request_middleware

from shuup_stripe.models import StripeCheckoutPaymentProcessor


def set_client_shop(client, shop):
    session = client.session
    session[SHOP_SESSION_KEY] = shop.id
    session.save()


@pytest.mark.django_db
def test_wizard_pane(rf, admin_user, settings):
    with override_settings(SHUUP_SETUP_WIZARD_PANE_SPEC=["shuup.admin.modules.service_providers.views.PaymentWizardPane"]):
        factories.get_default_shop()
        factories.get_default_tax_class()

        request = apply_request_middleware(rf.get("/"), user=admin_user)
        response = WizardView.as_view()(request)
        assert response.status_code == 200


@pytest.mark.django_db
@override_settings(
    SHUUP_ENABLE_MULTIPLE_SHOPS=True,
    SHUUP_SETUP_WIZARD_PANE_SPEC=["shuup.admin.modules.service_providers.views.PaymentWizardPane"]
)
def test_wizard_form(admin_user):
    shop1 = factories.get_shop(identifier="shop1", name="Shop 1", domain="shop-1", maintenance_mode=False)
    shop2 = factories.get_shop(identifier="shop2", name="Shop 2", domain="shop-2", maintenance_mode=False)

    shop1.staff_members.add(admin_user)
    shop2.staff_members.add(admin_user)

    client = Client()
    client.login(username=admin_user.username, password="password")

    # use shop2
    set_client_shop(client, shop2)

    with mock.patch("stripe.Account.retrieve") as retrieve_mocked:
        retrieve_mocked.return_value = None

        response = client.get(reverse("shuup_admin:wizard") + "?pane_id=payment")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Accept credit cards using" in content
        assert "https://stripe.com/" in content
        assert "Don't have a Stripe account?" in content

        payment_processor = StripeCheckoutPaymentProcessor.objects.create(
            secret_key="secret", publishable_key="12", name="Stripe")

        response = client.get(reverse("shuup_admin:wizard") + "?pane_id=payment")
        assert response.status_code == 200
        content = response.content.decode("utf-8")

        payment_processor.create_service(
            None, shop=shop2, tax_class=factories.get_default_tax_class(), enabled=True, name="Stripe")
        response = client.get(reverse("shuup_admin:wizard") + "?pane_id=payment")
        assert response.status_code == 200
        content = response.content.decode("utf-8")

        assert 'name="stripe-service_name"' in content
        assert 'name="stripe-secret_key"' in content
        assert 'name="stripe-publishable_key"' in content
