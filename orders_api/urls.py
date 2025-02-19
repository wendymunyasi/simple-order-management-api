"""
URL configuration for orders_api app.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    CreateAdminView,
    LoginView,
    LogoutView,
    OrderViewSet,
    ProductViewSet,
    PromoteToAdminView,
    RegisterView,
)

router = DefaultRouter()

router.register(r"products", ProductViewSet, basename="product")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"categories", CategoryViewSet, basename="category")


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("create-admin/", CreateAdminView.as_view(), name="create-admin"),
    path("promote-to-admin/", PromoteToAdminView.as_view(), name="promote-to-admin"),
    path("", include(router.urls)),
]
