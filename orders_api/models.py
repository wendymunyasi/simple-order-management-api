"""
Module for creating the models for the API.
"""

from django.contrib.auth.models import User
from django.db import models


class Category(models.Model):
    """
    Represents a category of products.

    Attributes:
        name (str): The name of the category. Must be unique.
    """

    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        """Returns the string representation of the product."""
        return str(self.name)


class Product(models.Model):
    """
    Model to represent products in the system.

    Attributes:
        name (str): The name of the product.
        image_url (str): The URL of the product's image.
        product_url (str): The URL of the product's page.
        cost_price (Decimal): The cost price of the product.
        price (Decimal): The selling price of the product.
        category (Category): The category to which the product belongs.
        reviews (int): The number of reviews the product has received.
        stars (Decimal): The average star rating of the product.
        is_best_seller (bool): Indicates whether the product is a bestseller.
        quantity (int): The available quantity of the product in stock.

    """

    name = models.CharField(max_length=255, help_text="The name of the product.")
    image_url = models.URLField(help_text="The URL of the product's image.")
    product_url = models.URLField(help_text="The URL of the product's page.")
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="The cost price of the product."
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="The selling price of the product."
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        help_text="The category to which the product belongs.",
    )
    reviews = models.PositiveIntegerField(
        help_text="The number of reviews the product has received."
    )
    stars = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        help_text="The average star rating of the product.",
    )
    is_best_seller = models.BooleanField(
        default=False, help_text="Indicates whether the product is a bestseller."
    )
    quantity = models.PositiveIntegerField(
        help_text="The available quantity of the product in stock."
    )

    def __str__(self):
        """Returns the string representation of the product."""
        return f"{self.id} - Name - {self.name}"  # pylint: disable=no-member


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
