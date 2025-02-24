"""
Module for creating the models for the API.
"""

import uuid

from cloudinary.models import CloudinaryField
from django.contrib.auth.models import User
from django.db import models, transaction


class Category(models.Model):
    """
    Represents a category of products.

    Attributes:
        id (UUID): The unique identifier for the category.
        name (str): The name of the category. Must be unique.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        """Meta class to define metadata for the model"""

        ordering = ["name"]  # Sort categories by id in ascending order
        verbose_name_plural = "Categories"

    def __str__(self):
        """Returns the string representation of the product."""
        return f"{self.name} - Category id - {self.id}"  # pylint: disable=no-member


class Product(models.Model):
    """
    Model to represent products in the system.

    Attributes:
        id (UUID): The unique identifier for the product.
        name (str): The name of the product.
        image(image): The product's image.
        product_url (str): The URL of the product's page.
        cost_price (Decimal): The cost price of the product.
        price (Decimal): The selling price of the product.
        category (Category): The category to which the product belongs.
        reviews (int): The number of reviews the product has received.
        stars (Decimal): The average star rating of the product.
        is_best_seller (bool): Indicates whether the product is a bestseller.
        quantity (int): The available quantity of the product in stock.

    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=1000, help_text="The name of the product.")
    image = CloudinaryField("image", help_text="The image of the product.")
    product_url = models.URLField(
        max_length=1000, help_text="The URL of the product's page."
    )
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
        help_text="The number of reviews the product has received.",
        blank=True,
        null=True,
        default=0,
    )
    stars = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        help_text="The average star rating of the product.",
        blank=True,
        null=True,
        default=0,
    )
    is_best_seller = models.BooleanField(
        default=False,
        help_text="Indicates whether the product is a bestseller.",
        blank=True,
        null=True,
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
        id (UUID): The unique identifier for the order.
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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        """
        Override save to:
        1. Adjust the product's stock based on the difference between the old and new quantities.
        2. Validate stock availability for updates.
        3. Calculate the total price of the order.
        """
        with transaction.atomic():
            # Check if this is an update (self.pk is not None)
            if self.pk:
                try:
                    # Fetch the old quantity from the database
                    old_order = Order.objects.get(  # pylint: disable=no-member
                        pk=self.pk
                    )
                    old_quantity = old_order.quantity
                except Order.DoesNotExist:  # pylint: disable=no-member
                    # Handle the edge case where the order does not exist
                    old_quantity = 0
            else:
                # New order, no previous quantity
                old_quantity = 0

            # Calculate the difference between the new and old quantities
            quantity_difference = self.quantity - old_quantity

            # Adjust the product's stock based on the difference
            if quantity_difference > 0:  # Increasing the order quantity
                if self.product.quantity < self.quantity:  # pylint: disable=no-member
                    raise ValueError(
                        f"Insufficient stock for product '{self.product.name}'. "
                        f"Available: {self.product.quantity}, Requested increase: {quantity_difference}."  # pylint: disable=no-member
                    )
                self.product.quantity -= quantity_difference  # Deduct the difference # pylint: disable=no-member
            elif quantity_difference < 0:  # De the order quantity
                self.product.quantity += abs(  # pylint: disable=no-member
                    quantity_difference
                )  # Add back the difference

            # Save the updated product stock
            self.product.save()  # pylint: disable=no-member

            # Calculate the total price
            self.total_price = (
                self.quantity * self.product.price  # pylint: disable=no-member
            )

            # Save the order
            super().save(*args, **kwargs)

    def __str__(self):
        """Returns the string representation of the order."""
        # Ensure self.id and self.user.username exist
        if hasattr(self, "id") and hasattr(self.user, "username"):
            return f"Order {self.id} by {self.user.username}"
        else:
            return "Order information is incomplete."

    def cancel_order(self):
        """
        Cancel the order and restore the product's quantity.
        """
        if self.status == "cancelled":
            raise ValueError("Order is already cancelled.")  # Prevent double cancelling

        with transaction.atomic():
            # Restore the product's quantity
            self.product.quantity += self.quantity  # pylint: disable=no-member
            self.product.save()  # pylint: disable=no-member

            # Mark the order as cancelled
            self.status = "cancelled"
            super().save()
