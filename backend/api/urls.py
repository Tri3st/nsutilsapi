from django.urls import path
from .views import text_to_image

urlpatterns = [
    path("api/text-to-image/", text_to_image, name="text_to_image"),
]
