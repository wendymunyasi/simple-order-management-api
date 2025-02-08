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

from .models import Order, Product
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    OrderRequestSerializer,
    OrderResponseSerializer,
    ProductSerializer,
    RegisterSerializer,
)


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


class OrderViewSet(viewsets.ModelViewSet):
    """Viewset for managing orders."""

    queryset = Order.objects.all().order_by("-updated_at")  # pylint: disable=no-member
    # serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request type."""
        if self.action in ["create", "update", "partial_update"]:
            return OrderRequestSerializer
        return OrderResponseSerializer

    def get_queryset(self):
        """Filter orders by the logged-in user."""
        return self.queryset.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Retrieve a list of all orders for the logged-in user.",
        responses={200: OrderResponseSerializer(many=True)},
        tags=["Orders"],
    )
    def list(self, request, *args, **kwargs):
        """Retrieve all orders for the logged-in user."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create a new order.",
        request_body=OrderRequestSerializer,
        responses={
            201: openapi.Response(
                "Order successfully created, well done, champ!",
                OrderResponseSerializer,
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
        self.perform_create(serializer)

        # Generate any additional headers for the response
        headers = self.get_success_headers(serializer.data)

        # Serialise the created order instance using the response serializer
        serializer = OrderResponseSerializer(serializer.instance)

        # Return a custom response with message
        return Response(
            {
                "message": "Order successfully created, well done, champ!",
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
                OrderRequestSerializer,
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
        request_body=OrderRequestSerializer,
        responses={
            200: openapi.Response(
                "Order updated successfully.",
                OrderResponseSerializer,
            ),
            400: openapi.Response(
                "You can only update orders with a status of 'pending'."
            ),
        },
        tags=["Orders"],
    )
    def update(self, request, *args, **kwargs):
        """Allow updates only if the order status is 'pending'.
        Overrides the update method in the OrderViewSet.
        """
        order = self.get_object()

        # Check if the current status is 'pending'
        if order.status != "pending":
            return Response(
                {"error": "You can only update orders with a status of 'pending'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Proceed with the update if the status is 'pending'
        response = super().update(request, *args, **kwargs)

        # Serialise the updated order instance with the response serializer
        serializer = OrderResponseSerializer(order)

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
        responses={200: OrderResponseSerializer(many=True)},
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
