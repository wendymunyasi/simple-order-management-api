"""Module for swagger configs
"""

from drf_yasg import openapi

# Reusable Swagger Schemas
SWAGGER_SCHEMAS = {
    "register_request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "username": openapi.Schema(
                type=openapi.TYPE_STRING, description="Username"
            ),
            "email": openapi.Schema(type=openapi.TYPE_STRING, description="Email"),
            "password": openapi.Schema(
                type=openapi.TYPE_STRING, description="Password"
            ),
        },
        required=["username", "email", "password"],
    ),
    "login_request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "username": openapi.Schema(
                type=openapi.TYPE_STRING, description="Username"
            ),
            "password": openapi.Schema(
                type=openapi.TYPE_STRING, description="Password"
            ),
        },
        required=["username", "password"],
    ),
    "logout_request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "refresh": openapi.Schema(
                type=openapi.TYPE_STRING, description="Refresh token to blacklist."
            ),
        },
        required=["refresh"],
    ),
    "admin_request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "username": openapi.Schema(
                type=openapi.TYPE_STRING, description="Username"
            ),
            "email": openapi.Schema(type=openapi.TYPE_STRING, description="Email"),
            "password": openapi.Schema(
                type=openapi.TYPE_STRING, description="Password"
            ),
        },
        required=["username", "email", "password"],
    ),
    "promote_request_body": openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "username": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="The username of the user to promote to admin.",
            ),
        },
        required=["username"],
    ),
}

# Reusable Responses
SWAGGER_RESPONSES = {
    "created": openapi.Response("Resource created successfully."),
    "not_found": openapi.Response("Resource not found."),
    "success": openapi.Response("Operation completed successfully."),
    "unauthorised": openapi.Response("Unauthorised access."),
    "validation_error": openapi.Response("Validation errors."),
}
