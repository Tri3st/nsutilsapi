from django.urls import path
from .views import text_to_image, LoginView, LogoutView


urlpatterns = [
    path("api/text-to-image/", text_to_image, name="text_to_image"),
    path('api/login/', LoginView.as_view(), name='api-login'),
    path('api/logout/', LogoutView.as_view(), name='api-logout'),
]
