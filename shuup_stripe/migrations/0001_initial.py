# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shuup', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StripeCheckoutPaymentProcessor',
            fields=[
                ('paymentprocessor_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='shuup.PaymentProcessor', on_delete=models.CASCADE)),
                ('secret_key', models.CharField(max_length=100, verbose_name='Secret Key')),
                ('publishable_key', models.CharField(max_length=100, verbose_name='Publishable Key')),
            ],
            options={
                'abstract': False,
            },
            bases=('shuup.paymentprocessor',),
        ),
    ]
