# This file is part of Shuup Stripe Addon.
#
# Copyright (c) 2012-2018, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from shuup.apps.provides import get_provide_objects
from shuup.core.models import PaymentProcessor, ServiceChoice


class StripeCheckoutPaymentProcessor(PaymentProcessor):
    secret_key = models.CharField(max_length=255, verbose_name=_("Secret Key"))
    publishable_key = models.CharField(
        max_length=255, verbose_name=_("Publishable Key"))

    def get_service_choices(self):
        stripe_chargers = get_provide_objects("stripe_charger")
        return [
            ServiceChoice(stripe_charger.identifier, stripe_charger.name)
            for stripe_charger in stripe_chargers
        ]

    def process_payment_return_request(self, service, order, request):
        if not order.is_paid():
            stripe_chargers = get_provide_objects("stripe_charger")
            for stripe_charger in stripe_chargers:
                if stripe_charger.identifier == service.choice_identifier:
                    charger = stripe_charger(order=order, secret_key=self.secret_key)
                    charger.create_charge()


class StripeCustomer(models.Model):
    contact = models.OneToOneField(
        "shuup.Contact", verbose_name=_("contact"), related_name="stripe_customer", on_delete=models.CASCADE)
    customer_token = models.CharField(max_length=255, verbose_name=_("Stripe customer ID"))

    class Meta:
        verbose_name = _("Stripe Customer")
        verbose_name_plural = _("Stripe Customers")
