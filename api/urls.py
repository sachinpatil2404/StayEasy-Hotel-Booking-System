from django.urls import path
from .views import RegisterAPIView, LoginAPIView, RefreshAPIView,ProfileAPIView, HotelListAPIView

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),

    path("login/", LoginAPIView.as_view(), name="login"),

    path("refresh/", RefreshAPIView.as_view(), name="refresh"),

    path("profile/", ProfileAPIView.as_view(), name="profile"),

    path("hotels/", HotelListAPIView.as_view(), name="hotel-list"),
]