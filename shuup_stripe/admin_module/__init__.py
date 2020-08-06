# -*- coding: utf-8 -*-
# This file is part of Shuup Stripe Addon.
#
# Copyright (c) 2012-2018, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView
from shuup.admin.base import AdminModule
from shuup.admin.utils.urls import admin_url, get_model_url
from shuup.core.models import Order

from shuup_stripe.notify_events import SendStripePaymentLink


class SendPaymentLink(DetailView):
    model = Order

    def get(self, request, *args, **kwargs):
        order = self.object = self.get_object()
        billing_address = order.billing_address
        customer_email = (billing_address.email if billing_address and billing_address.email else order.email)
        if not customer_email:
            messages.error(self.request, _("Missing to email for the payment link."))
            return HttpResponseRedirect(get_model_url(self.get_object()))

        params = dict(
            order=order,
            customer_email=customer_email,
            payment_link=reverse("shuup:stripe_payment_view", kwargs={"pk": order.pk, "key": order.key}),
            language=order.language
        )
        SendStripePaymentLink(**params).run(shop=order.shop)
        messages.success(self.request, _("Payment link send!"))
        return HttpResponseRedirect(get_model_url(self.get_object()))


class StripeModule(AdminModule):
    name = _("Stripe Payments")

    def get_urls(self):
        return [
            admin_url(
                r"^stripe_payment_link/(?P<pk>\d+)/$",
                "shuup_stripe.admin_module.SendPaymentLink",
                name="shuup_stripe.payment_link"
            ),
        ]
