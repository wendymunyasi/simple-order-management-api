"""Module for creating the views for the API endpoints.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Category, Order, Product
from .serializers import (  # OrderSerializer,; OrderSerializer,
    BulkOrderSerializer,
    CategorySerializer,
    LoginSerializer,
    LogoutSerializer,
    OrderSerializer,
    ProductSerializer,
    RegisterSerializer,
)
from .swagger_config import SWAGGER_RESPONSES, SWAGGER_SCHEMAS
from .tasks import send_order_email


class RegisterView(APIView):
    """Handles the creation of new user accounts. Validates the input data
    and ensures that the email is unique.
    """

    @swagger_auto_schema(
        operation_description="Register a new user.",
        request_body=RegisterSerializer,
        responses={
            200: SWAGGER_RESPONSES["success"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["authentication"],
    )
    def post(self, request):
        """Handles POST requests to register a new user."""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User registered successfully"},
                status=status.HTTP_201_CREATED,
            )
        # Return validation errors if the serializer is invalid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(TokenObtainPairView):
    """Handles user authentication and returns JWT tokens (access and refresh)
    if the credentials are valid.
    """

    serializer_class = LoginSerializer

    @swagger_auto_schema(
        operation_description="Log in a user and retrieve JWT tokens.",
        request_body=LoginSerializer,
        responses={
            200: SWAGGER_RESPONSES["success"],
            401: SWAGGER_RESPONSES["unauthorised"],
        },
        tags=["authentication"],
    )
    def post(self, request, *args, **kwargs):
        """Handles POST requests to log in a user."""

        username = request.data.get("username")
        password = request.data.get("password")

        # Authenticate the user using Django's built-in authentication system
        user = authenticate(username=username, password=password)
        if user:
            # Generate JWT tokens for the authenticated user
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "message": "User logged in successfully.",  # Success message
                    "tokens": {  # Nest the tokens inside a "tokens" object
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                },
                status=status.HTTP_200_OK,
            )
        # Return an error response if authentication fails
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )


class LogoutView(APIView):
    """Handles the blacklisting of refresh tokens to ensure that they cannot
    be used to generate new access tokens after logout."""

    @swagger_auto_schema(
        operation_description="Log out a user.",
        request_body=LogoutSerializer,
        responses={
            205: SWAGGER_RESPONSES["success"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["authentication"],
    )
    def post(self, request):
        """Handles POST requests to log out a user."""
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User logged out successfully."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductViewSet(viewsets.ModelViewSet):
    """Viewset for managing products."""

    queryset = Product.objects.all()  # pylint: disable=no-member
    serializer_class = ProductSerializer

    def get_permissions(self):
        """
        Dynamically assign permissions based on the action.
        - Admin-only actions: create, update, destroy
        - Read-only actions: list, retrieve (accessible to all authenticated users)
        """
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [
                IsAuthenticated
            ]  # Allow all authenticated users to view
        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        """Pass the request to the serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @swagger_auto_schema(
        operation_description="Retrieve a list of all products.",
        responses={
            200: SWAGGER_RESPONSES["success"],
        },
        tags=["products"],
    )
    def list(self, request, *args, **kwargs):
        """Retrieve all products."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new product.",
        request_body=ProductSerializer,
        responses={
            201: SWAGGER_RESPONSES["created"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["products"],
    )
    def create(self, request, *args, **kwargs):
        """Override create to include a custom success message and check for dups."""

        # Extract the name and price from the request data
        name = request.data.get("name")
        price = request.data.get("price")

        # Check if a product with the same name (case-insensitive) and price already exists
        if Product.objects.filter(  # pylint: disable=no-member
            name__iexact=name, price=price
        ).exists():
            return Response(
                {"message": "Hold up, product already exists in the system."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initialize the serializer with the incoming request data
        serializer = self.get_serializer(data=request.data)

        # Validate the incoming data using the serializer
        serializer.is_valid(raise_exception=True)

        # Save the validated data to db
        self.perform_create(serializer)

        # Generate any additional headers for the response
        headers = self.get_success_headers(serializer.data)

        # Return a custom response with message
        return Response(
            {
                "message": "Product successfully created, well done, champ!",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @swagger_auto_schema(
        operation_description="Update a product in the system.",
        request_body=ProductSerializer,
        responses={
            200: SWAGGER_RESPONSES["success"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["products"],
    )
    def update(self, request, *args, **kwargs):
        """Override update to return a custom success message with product details."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {
                "message": "Product updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_description="Delete a product from the system.",
        responses={
            200: SWAGGER_RESPONSES["success"],
        },
        tags=["products"],
    )
    def destroy(self, request, *args, **kwargs):
        """Override destroy to return a custom success message."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Product deleted successfully."},
            status=status.HTTP_200_OK,
        )


class OrderViewSet(viewsets.ModelViewSet):
    """Viewset for managing orders."""

    queryset = Order.objects.all().order_by("-updated_at")  # pylint: disable=no-member
    # serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request type."""
        if self.action == "create":
            return BulkOrderSerializer  # Use BulkOrderSerializer for creation
        return OrderSerializer

    def get_queryset(self):
        """
        Filter orders by the logged-in user unless the user is an admin.
        Admins can view all orders.

        This method ensures that:
        1. If the view is being accessed by Swagger (for schema generation),
        it returns an empty queryset to avoid unnecessary errors.
        2. If the user is an admin, it returns all orders.
        3. If the user is authenticated, it filters the queryset to include
        only objects related to the logged-in user.
        4. If the user is not authenticated, it returns an empty queryset.
        """
        # Return an empty queryset if the view is being accessed by Swagger
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()

        # If the user is an admin, return all orders
        if self.request.user.is_staff:
            return self.queryset

        # If the user is authenticated, return only their orders
        if self.request.user.is_authenticated:
            return self.queryset.filter(user=self.request.user)

        # If the user is not authenticated, return an empty queryset
        return self.queryset.none()

    @swagger_auto_schema(
        operation_description="Retrieve a list of all orders for the logged-in user.",
        responses={
            200: SWAGGER_RESPONSES["success"],
        },
        tags=["orders"],
    )
    def list(self, request, *args, **kwargs):
        """Retrieve all orders for the logged-in user."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create one or more orders.",
        request_body=BulkOrderSerializer,
        responses={
            201: SWAGGER_RESPONSES["success"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["orders"],
    )
    def create(self, request, *args, **kwargs):
        """Override create to include a custom success message."""

        # Initialize the serializer with the incoming request data
        serializer = self.get_serializer(data=request.data)

        # Validate the incoming data using the serializer
        serializer.is_valid(raise_exception=True)

        # Save the validated data to db
        _ = serializer.save()

        # Generate any additional headers for the response
        headers = self.get_success_headers(serializer.data)

        # Trigger the email task
        user_email = request.user.email
        send_order_email.delay(serializer.data, user_email)

        # Return a custom response with message
        return Response(
            {
                "message": "Order(s) successfully created, well done, champ!",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @swagger_auto_schema(
        operation_description="Cancel an order by marking it as cancelled.",
        responses={
            200: SWAGGER_RESPONSES["success"],
        },
        tags=["orders"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft delete an order by marking it as cancelled.
        Overrides the destroy method in the OrderViewSet."""

        # Retrieve the order instance
        order = self.get_object()

        try:
            # Call the cancel_order method to restore stock and mark as cancelled
            order.cancel_order()
            return Response(
                {"message": "Order cancelled successfully."},
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            # Handle the case where the order is already cancelled
            return Response(
                {"message": str(e)},  # Return the error message
                status=status.HTTP_400_BAD_REQUEST,
            )

    @swagger_auto_schema(
        operation_description="Update an order if it's status is 'pending'.",
        request_body=OrderSerializer,
        responses={
            200: SWAGGER_RESPONSES["success"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["orders"],
    )
    def update(self, request, *args, **kwargs):
        """Allow updates only if the order status is 'pending' and only if the product_id
        matches the existing product_id in the order.
        Overrides the update method in the OrderViewSet.
        """
        order = self.get_object()

        # Check if the current status is 'pending'
        if order.status != "pending":
            return Response(
                {"error": "You can only update orders with a status of 'pending'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if the product_id in the request matches the existing product_id
        request_product_id = request.data.get("product_id")
        if request_product_id and str(request_product_id) != str(order.product.id):
            return Response(
                {
                    "error": "You can only update a product id that exists in this order."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Proceed with the update if validations pass
        response = super().update(request, *args, **kwargs)

        # Refresh the order instance to get the latest data from the database
        order.refresh_from_db()

        # Serialise the updated order instance with the response serializer
        serializer = OrderSerializer(order)

        # Add a custom success message to the response
        return Response(
            {
                "message": "Order updated successfully.",
                "data": serializer.data,  # Include the updated order data
            },
            status=response.status_code,
        )

    @swagger_auto_schema(
        operation_description="Filter orders based on query parameters.",
        manual_parameters=[
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter orders by status (e.g., 'pending', 'completed').",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "product_name",
                openapi.IN_QUERY,
                description="Filter orders by product name.",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "ordering",
                openapi.IN_QUERY,
                description="Order by fields (e.g., 'created_at', '-updated_at').",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={
            200: SWAGGER_RESPONSES["success"],
        },
        tags=["orders"],
    )
    @action(detail=False, methods=["get"], url_path="search")
    def filter_orders(self, request):
        """
        Custom endpoint to filter orders based on query parameters.

        Query Parameters:
            - status (Optional): Filter orders by status (e.g., 'pending', 'completed').
            - product_name (Optional): Filter orders by product name.
            - ordering (Optional): Order by fields (e.g., 'created_at', '-updated_at').

        Returns:
            list: Filtered orders based on the provided query parameters.
        """
        status_param = request.query_params.get("status", None)
        product_name = request.query_params.get("product_name", None)
        ordering = request.query_params.get("ordering", None)

        # Start with the base queryset filtered by the logged-in user
        orders = self.get_queryset()

        # Apply filters based on query parameters
        if status_param:
            orders = orders.filter(status=status_param)
        if product_name:
            orders = orders.filter(product__name__icontains=product_name)
        if ordering:
            orders = orders.order_by(ordering)

        # Apply pagination
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Serialize the filtered orders and if no pagination is applied, return the full list
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ModelViewSet):
    """Viewset for managing categories."""

    queryset = Category.objects.all()  # pylint: disable=no-member
    serializer_class = CategorySerializer

    def get_permissions(self):
        """
        Dynamically assign permissions based on the action.
        - Admin-only actions: create, update, destroy
        - Read-only actions: list, retrieve (accessible to all authenticated users)
        """
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [
                IsAuthenticated
            ]  # Allow all authenticated users to view
        return [permission() for permission in permission_classes]

    def get_serializer_context(self):
        """Pass the request to the serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @swagger_auto_schema(
        operation_description="Retrieve a list of all categories.",
        responses={
            200: SWAGGER_RESPONSES["success"],
        },
        tags=["categories"],
    )
    def list(self, request, *args, **kwargs):
        """Retrieve all categories."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new category.",
        request_body=CategorySerializer,
        responses={
            201: SWAGGER_RESPONSES["created"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["categories"],
    )
    def create(self, request, *args, **kwargs):
        """Override create to include a custom success message and check for dups."""

        # Extract the name and price from the request data
        name = request.data.get("name")

        # Check if a product with the same name (case-insensitive) and price already exists
        if Category.objects.filter(  # pylint: disable=no-member
            name__iexact=name,
        ).exists():
            return Response(
                {"message": "Hold up, category already exists in the system."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initialize the serializer with the incoming request data
        serializer = self.get_serializer(data=request.data)

        # Validate the incoming data using the serializer
        serializer.is_valid(raise_exception=True)

        # Save the validated data to db
        self.perform_create(serializer)

        # Generate any additional headers for the response
        headers = self.get_success_headers(serializer.data)

        # Return a custom response with message
        return Response(
            {
                "message": "Category successfully created, well done, champ!",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @swagger_auto_schema(
        operation_description="Update a category in the system.",
        request_body=CategorySerializer,
        responses={
            200: SWAGGER_RESPONSES["success"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["categories"],
    )
    def update(self, request, *args, **kwargs):
        """Override update to return a custom success message with category details."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {
                "message": "Category updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_description="Delete a category from the system.",
        responses={
            200: SWAGGER_RESPONSES["success"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["categories"],
    )
    def destroy(self, request, *args, **kwargs):
        """Override destroy to return a custom success message."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Category deleted successfully."},
            status=status.HTTP_200_OK,
        )


class CreateAdminView(APIView):
    """
    API endpoint to allow superusers to create admin accounts.
    """

    permission_classes = [IsAdminUser]  # Only superusers can access this endpoint

    @swagger_auto_schema(
        operation_description="Create a new admin account (superuser only).",
        request_body=SWAGGER_SCHEMAS["admin_request_body"],
        responses={
            201: SWAGGER_RESPONSES["created"],
            400: SWAGGER_RESPONSES["validation_error"],
        },
        tags=["admin management"],
    )
    def post(self, request):
        """Create a new admin account."""
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not email or not password:
            return Response(
                {"error": "Username, email, and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Validate the email format
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"error": "Invalid email format."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Check if the username or email already exists
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "A user with this username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the admin user
        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.is_staff = True  # Mark the user as an admin
        user.save()

        return Response(
            {"message": f"Admin account for {username} created successfully."},
            status=status.HTTP_201_CREATED,
        )


class PromoteToAdminView(APIView):
    """
    API endpoint to allow superusers to promote users to admin status.
    """

    permission_classes = [IsAdminUser]  # Only superusers can access this endpoint

    @swagger_auto_schema(
        operation_description="Promote a user to admin status (superuser only).",
        request_body=SWAGGER_SCHEMAS["promote_request_body"],
        responses={
            200: SWAGGER_RESPONSES["success"],
            400: SWAGGER_RESPONSES["validation_error"],
            404: SWAGGER_RESPONSES["not_found"],
        },
        tags=["admin management"],
    )
    def post(self, request):
        """Promote a user to admin status."""
        username = request.data.get("username")

        if not username:
            return Response(
                {"error": "Username is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:  # pylint: disable=no-member
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_staff:
            return Response(
                {"message": f"User {username} is already an admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_staff = True  # Promote the user to admin
        user.save()

        return Response(
            {"message": f"User {username} has been promoted to admin."},
            status=status.HTTP_200_OK,
        )
