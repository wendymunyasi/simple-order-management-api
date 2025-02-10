"""Module for serializing the models so that they can be exposed to the API.
They only validate the data. Responses are created in the views because they
handle HTTP requests and response cycles.
"""

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Category, Order, Product


class RegisterSerializer(serializers.ModelSerializer):
    """Serialzier to map the User model to the JSON format"""

    email = serializers.EmailField(required=True)  # Explicitly set email as required

    class Meta:
        """Meta class to define the model and fields to include in the serializer."""

        model = User
        fields = ["username", "password", "email"]
        extra_kwargs = {"password": {"write_only": True}}

    class SwaggerExamples:  # pylint: disable=too-few-public-methods
        """Swagger examples for the RegisterSerializer."""

        example = {
            "username": "tevin",
            "password": "password",
            "email": "9WYnF@example.com",
        }

    def validate_email(self, value):
        """
        Validates the email field to ensure uniqueness.

        Args:
            value (str): The email address provided by the user.

        Returns:
            str: The validated email address.

        Raises:
            serializers.ValidationError: If the email already exists.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "User with that email exists, please log in."
            )
        return value

    def create(self, validated_data):
        """
        Creates a new user with the validated data.

        Args:
            validated_data (dict): The validated user data.

        Returns:
            User: The newly created user instance.
        """
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for user login.

    Handles the validation of user credentials (username and password).
    It ensures that the required fields are provided.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    class SwaggerExamples:  # pylint: disable=too-few-public-methods
        """Swagger examples for the LoginSerializer."""

        example = {
            "username": "tevin",
            "password": "password",
        }


class LogoutSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    """
    Serializer for user logout.

    Handles the validation and blacklisting of the refresh token
    during the logout process.
    Blacklisting ensures that the token cannot be used to generate new access
    tokens after the user logs out.

    Fields:
        - refresh: The refresh token to be blacklisted.

    Methods:
        - validate: Validates the refresh token and stores it for further processing.
        - save: Blacklists the refresh token to prevent further use.
    """

    refresh = serializers.CharField()

    def __init__(self, *args, **kwargs):
        """
        Initializes the serializer and sets the `token` attribute to None.
        """
        super().__init__(*args, **kwargs)
        self.token = None  # Initialize the token attribute

    def validate(self, attrs):
        """
        Validates the refresh token and stores it for further processing.

        Args:
            attrs (dict): The data passed to the serializer.

        Returns:
            dict: The validated data.
        """
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        """
        Blacklists the refresh token to prevent further use.
        If the token is invalid or cannot be blacklisted, an exception is raised.

        Raises:
            ValidationError: If the token is invalid or cannot be blacklisted.
        """
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:  # Catch only TokenError
            self.fail("bad_token")


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for the Product model."""

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        """Meta class to define the model and fields to include in the serializer."""

        model = Product
        fields = [
            "id",
            "name",
            "cost_price",
            "price",
            "quantity",
            "image_url",
            "product_url",
            "reviews",
            "stars",
            "is_best_seller",
            "category",
            "category_name",
        ]

    class SwaggerExamples:
        """Swagger examples for the ProductSerializer."""

        example = {
            "id": 1,
            "name": "Lotion Eos Product",
            "cost_price": 100,
            "price": 100,
            "quantity": 1,
            "image_url": "https://example.com/image.jpg",
            "product_url": "https://example.com/product",
            "reviews": 10,
            "stars": 4.5,
            "is_best_seller": True,
            "category": 1,
            "category_name": "Lotion",
        }

    def __init__(self, *args, **kwargs):
        """
        Dynamically modify fields based on the request type.
        For GET requests, exclude 'cost_price' and 'category'.
        This 'category' stands for the category.id here. Otherwise the name of the category
        will still display under 'category_name'.
        """
        super().__init__(*args, **kwargs)

        # Check if the context contains the request
        request = self.context.get("request")
        if request and request.method == "GET":
            # Exclude 'cost_price' and 'category' for GET requests
            excluded_fields = ["cost_price", "category"]
            for field in excluded_fields:
                self.fields.pop(field)


class OrderRequestSerializer(serializers.ModelSerializer):
    """Serializer for for returning order details (response body)."""

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),  # pylint: disable=no-member
        source="product",  # Map product_id to the product field in the model
        write_only=True,  # pylint: disable=no-member
    )

    class Meta:
        """Meta class to define the model and fields to include in the serializer."""

        model = Order
        fields = [
            "product_id",
            "quantity",
        ]

    class SwaggerExamples:
        """Swagger examples for the OrderRequestSerializer."""

        example = {
            "product_id": 1,
            "quantity": 1,
        }

    def validate_quantity(self, value):
        """Ensure quantity is greater than 0."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def create(self, validated_data):
        """Set the user automatically when creating an order."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class OrderResponseSerializer(serializers.ModelSerializer):
    """Serializer for returning order details (response body)."""

    user = serializers.StringRelatedField(read_only=True)  # Show username instead of ID
    product = ProductSerializer(read_only=True)  # Nested product details

    class Meta:
        """Meta class to define the model and fields for the response serializer."""

        model = Order
        fields = [
            "id",
            "user",
            "product",
            "quantity",
            "total_price",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields  # All fields are read-only in the response

    class SwaggerExamples:
        """Swagger examples for the OrderResponseSerializer."""

        example = {
            "id": 1,
            "user": "John Doe",
            "product": {
                "id": 1,
                "name": "Lotion Eos Product",
                "price": 100,
            },
            "quantity": 1,
            "total_price": 100,
            "status": "pending",
            "created_at": "2021-01-01T00:00:00Z",
            "updated_at": "2021-01-01T00:00:00Z",
        }


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for the Category model."""

    class Meta:
        """Meta class to define the model and fields to include in the serializer."""

        model = Category
        fields = [
            "id",
            "name",
        ]

    class SwaggerExamples:
        """Swagger examples for the ProductSerializer."""

        example = {
            "id": 1,
            "name": "Lotion",
        }
