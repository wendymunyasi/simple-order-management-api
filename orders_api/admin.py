"""Module to register the models in admin panel
"""

from django.contrib import admin

from .models import Category, Order, Product

admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Category)
