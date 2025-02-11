# Generated by Django 5.1.6 on 2025-02-10 14:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders_api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='image_url',
            field=models.URLField(help_text="The URL of the product's image.", max_length=1000),
        ),
        migrations.AlterField(
            model_name='product',
            name='product_url',
            field=models.URLField(help_text="The URL of the product's page.", max_length=1000),
        ),
    ]
