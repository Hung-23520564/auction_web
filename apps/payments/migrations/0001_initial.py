# Generated by Django 5.1.6 on 2025-06-02 08:21

import apps.payments.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('items', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('transaction_id', models.AutoField(primary_key=True, serialize=False)),
                ('final_price', models.DecimalField(decimal_places=2, max_digits=15)),
                ('status', models.CharField(choices=[('pending', 'Pending Sale'), ('pending_admin_confirmation', 'Pending Admin Confirmation'), ('completed', 'Completed'), ('failed', 'Failed'), ('expired', 'Expired')], default='pending', max_length=30)),
                ('transaction_type', models.CharField(choices=[('sale', 'Sale'), ('deposit', 'Deposit'), ('withdrawal', 'Withdrawal')], default='sale', max_length=15)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('expires_date', models.DateTimeField(blank=True, default=apps.payments.models.get_default_expires_date, null=True)),
                ('buyer_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='initiated_transactions', to=settings.AUTH_USER_MODEL)),
                ('item_id', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='items.item')),
                ('seller_id', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'transactions',
                'ordering': ['-created_date'],
            },
        ),
    ]
