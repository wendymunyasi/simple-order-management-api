"""
Module for creating the models for the API.
"""

from django.contrib.auth.models import User
from django.db import models


class Product(models.Model):
    """
    Model to represent products in the system.

    Attributes:
        name (str): The name of the product.
        price (Decimal): The price of the product.
    """

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        """Returns the string representation of the product."""
        return str(self.name)


class Order(models.Model):
    """
    Model to represent orders in the system.

    Attributes:
        user (User): The user who placed the order.
        product (Product): The product being ordered.
        quantity (int): The quantity of the product ordered.
        total_price (Decimal): The total price of the order.
        status (str): The status of the order (e.g., pending, shipped, delivered, cancelled).
        created_at (datetime): The timestamp when the order was created.
        updated_at (datetime): The timestamp when the order was last updated.

    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="orders"
    )
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """Override save to calculate total_price."""
        # Ensure self.product is a valid Product instance
        if self.product and hasattr(self.product, "price"):
            self.total_price = self.quantity * self.product.price
        else:
            raise ValueError("Product or its price is not defined.")
        super().save(*args, **kwargs)

    def __str__(self):
        """Returns the string representation of the order."""
        # Ensure self.id and self.user.username exist
        if hasattr(self, "id") and hasattr(self.user, "username"):
            return f"Order {self.id} by {self.user.username}"
        else:
            return "Order information is incomplete."
