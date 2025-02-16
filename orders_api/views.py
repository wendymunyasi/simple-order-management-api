"""Module for creating the views for the API endpoints.
"""

from django.contrib.auth import authenticate
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
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
from .tasks import send_order_email


class RegisterView(APIView):
    """Handles the creation of new user accounts. Validates the input data
    and ensures that the email is unique.
    """

    @swagger_auto_schema(
        operation_description="Register a new user.",
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response("User registered successfully."),
            400: openapi.Response("User or email already registered. Please login."),
        },
        tags=["Authentication"],
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
            200: openapi.Response(
                "User logged in successfully.",
                examples={
                    "application/json": {
                        "message": "User logged in successfully.",
                        "tokens": {
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 ....",
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                    }
                },
            ),
            401: openapi.Response("Invalid credentials."),
        },
        tags=["Authentication"],
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
            205: openapi.Response("User logged out successfully."),
            400: openapi.Response("Validation errors."),
        },
        tags=["Authentication"],
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
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        """Pass the request to the serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @swagger_auto_schema(
        operation_description="Retrieve a list of all products.",
        responses={200: ProductSerializer(many=True)},
        tags=["Products"],
    )
    def list(self, request, *args, **kwargs):
        """Retrieve all products."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new product.",
        request_body=ProductSerializer,
        responses={
            201: openapi.Response(
                "Product successfully created, well done, champ!",
                ProductSerializer,
            ),
            400: openapi.Response("Hold up, product already exists in the system."),
        },
        tags=["Products"],
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
            200: openapi.Response(
                "Product updated successfully.",
                ProductSerializer,
            ),
        },
        tags=["Products"],
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
            200: openapi.Response(
                "Product deleted successfully.",
            ),
        },
        tags=["Products"],
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
        """Filter orders by the logged-in user."""
        return self.queryset.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Retrieve a list of all orders for the logged-in user.",
        responses={200: OrderSerializer(many=True)},
        tags=["Orders"],
    )
    def list(self, request, *args, **kwargs):
        """Retrieve all orders for the logged-in user."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create one or more orders.",
        request_body=BulkOrderSerializer,
        responses={
            201: openapi.Response(
                "Order successfully created, well done, champ!",
                OrderSerializer,
            ),
            400: openapi.Response("Validation errors."),
        },
        tags=["Orders"],
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
            200: openapi.Response(
                "Order cancelled successfully.",
                OrderSerializer,
            ),
        },
        tags=["Orders"],
    )
    def destroy(self, request, *args, **kwargs):
        """Soft delete an order by marking it as cancelled.
        Overrides the destroy method in the OrderViewSet."""

        # Retrieve the order instance that the user is requesting
        order = self.get_object()

        order.status = "cancelled"  # Cancel the order
        order.save()  # Save the order and return a response
        return Response(
            {"message": "Order cancelled successfully."}, status=status.HTTP_200_OK
        )

    @swagger_auto_schema(
        operation_description="Update an order if it's status is 'pending'.",
        request_body=OrderSerializer,
        responses={
            200: openapi.Response(
                "Order updated successfully.",
                OrderSerializer,
            ),
            400: openapi.Response(
                "You can only update orders with a status of 'pending'."
            ),
        },
        tags=["Orders"],
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
        if request_product_id and int(request_product_id) != order.product.id:
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
        responses={200: OrderSerializer(many=True)},
        tags=["Orders"],
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
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        """Pass the request to the serializer context."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @swagger_auto_schema(
        operation_description="Retrieve a list of all categories.",
        responses={200: CategorySerializer(many=True)},
        tags=["Categories"],
    )
    def list(self, request, *args, **kwargs):
        """Retrieve all categories."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new category.",
        request_body=CategorySerializer,
        responses={
            201: openapi.Response(
                "Category successfully created, well done, champ!",
                CategorySerializer,
            ),
            400: openapi.Response("Hold up, category already exists in the system."),
        },
        tags=["Categories"],
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
            200: openapi.Response(
                "Category updated successfully.",
                CategorySerializer,
            ),
        },
        tags=["Categories"],
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
            200: openapi.Response(
                "Product deleted successfully.",
            ),
        },
        tags=["Categories"],
    )
    def destroy(self, request, *args, **kwargs):
        """Override destroy to return a custom success message."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Category deleted successfully."},
            status=status.HTTP_200_OK,
        )
