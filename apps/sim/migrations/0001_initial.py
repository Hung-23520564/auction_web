# Generated by Django 5.2 on 2025-05-28 15:47

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the auction item', max_length=200)),
                ('description', models.TextField(help_text='Detailed description of the item')),
                ('starting_price', models.DecimalField(decimal_places=2, help_text='Starting bid price in VND', max_digits=10)),
                ('current_price', models.DecimalField(decimal_places=2, default=0.0, help_text='Current highest bid', max_digits=10)),
                ('end_time', models.DateTimeField(help_text='Auction end time')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text='The public id of the uploaded file', max_length=100)),
                ('url', models.CharField(max_length=100)),
                ('name', models.CharField(help_text='The original name of the uploaded image', max_length=100)),
                ('width', models.IntegerField(help_text='Width in pixels')),
                ('height', models.IntegerField(help_text='Height in pixels')),
                ('format', models.CharField(max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(blank=True, help_text='Associated auction item', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='sim.item')),
            ],
        ),
    ]
