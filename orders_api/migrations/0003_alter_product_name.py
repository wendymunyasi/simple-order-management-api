# Generated by Django 5.1.6 on 2025-02-10 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders_api', '0002_alter_product_image_url_alter_product_product_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='name',
            field=models.CharField(help_text='The name of the product.', max_length=1000),
        ),
    ]
