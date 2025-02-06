"""Module for serializing the models so that they can be exposed to the API.
They only validate the data. Responses are created in the views because they
handle HTTP requests and response cycles.
"""

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Order, Product


class RegisterSerializer(serializers.ModelSerializer):
    """Serialzier to map the User model to the JSON format"""

    email = serializers.EmailField(required=True)  # Explicitly set email as required

    class Meta:
        """Meta class to define the model and fields to include in the serializer."""

        model = User
        fields = ["username", "password", "email"]
        extra_kwargs = {"password": {"write_only": True}}

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

    class Meta:
        """Meta class to define the model and fields to include in the serializer."""

        model = Product
        fields = ["id", "name", "price"]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for the Order model."""

    user = serializers.StringRelatedField(read_only=True)  # Show username instead of ID
    product = ProductSerializer(read_only=True)  # Nested product details
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),  # pylint: disable=no-member
        source="product",  # Map product_id to the product field in the model
        write_only=True,  # pylint: disable=no-member
    )

    class Meta:
        """Meta class to define the model and fields to include in the serializer."""

        model = Order
        fields = [
            "id",
            "user",
            "product",
            "product_id",
            "quantity",
            "total_price",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["total_price", "created_at", "updated_at"]

    def validate_quantity(self, value):
        """Ensure quantity is greater than 0."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def create(self, validated_data):
        """Set the user automatically when creating an order."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
