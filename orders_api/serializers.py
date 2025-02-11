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
            "category",
            "cost_price",
            "price",
            "quantity",
            "image",
            "image",
            "product_url",
            "reviews",
            "stars",
            "is_best_seller",
            "category_name",
        ]

        extra_kwargs = {  # These fields will not be included in POST requests
            "reviews": {"required": False, "default": 0, "read_only": True},
            "stars": {"required": False, "default": 0, "read_only": True},
            "is_best_seller": {"required": False, "default": False, "read_only": True},
        }

    class SwaggerExamples:
        """Swagger examples for the ProductSerializer."""

        example = {
            "id": 1,
            "name": "Lotion Eos Product",
            "category": 1,
            "cost_price": "100",
            "price": "120",
            "quantity": 1,
            "image": "image.jpg",
            "product_url": "https://example.com/product",
            "reviews": 10,
            "stars": 4.5,
            "is_best_seller": True,
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
                self.fields.pop(field, None)


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for handling both request and response for orders."""

    product = serializers.SerializerMethodField(
        read_only=True
    )  # Customised product details
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),  # pylint: disable=no-member
        source="product",  # Map product_id to the product field in the model
        write_only=True,  # pylint: disable=no-member
    )
    user = serializers.StringRelatedField(read_only=True)  # Show username instead of ID

    class Meta:
        """Meta class to define the model and fields for the serializer."""

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
        extra_kwargs = {
            "user": {"read_only": True},
            "total_price": {"read_only": True},
            "status": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def __init__(self, *args, **kwargs):
        """Customise fields based on the context (request vs response)."""
        super().__init__(*args, **kwargs)

        # If this is a request (e.g., POST), remove response-only fields
        if self.context.get("request") and self.context["request"].method in [
            "POST",
            "PUT",
            "PATCH",
        ]:
            self.fields.pop("id", None)
            self.fields.pop("user", None)
            self.fields.pop("product", None)
            self.fields.pop("total_price", None)
            self.fields.pop("status", None)
            self.fields.pop("created_at", None)
            self.fields.pop("updated_at", None)

    def get_product(self, obj):
        """Customise the product field in the response."""
        product = obj.product
        return {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "image": (
                str(product.image.url) if product.image else None
            ),  # Convert to URL string
            "product_url": product.product_url,
            "category_name": product.category.name,  # Assuming category is a related field
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
