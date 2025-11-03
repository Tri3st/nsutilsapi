from django.urls import path
from .views import text_to_image, LoginView, LogoutView, upload_foto, upload_fotos, UserInfoView


print(f"LogoutView is : {LogoutView}, type: {type(LogoutView)}")

urlpatterns = [
    path("text-to-image/", text_to_image, name="text_to_image"),
    path('upload-foto/', upload_foto, name="upload_foto"),
    path('upload-fotos/', upload_fotos, name="upload_fotos"),
    path('userinfo/', UserInfoView.as_view(), name='userinfo'),
    path('login/', LoginView.as_view(), name='api-login'),
    path('logout/', LogoutView.as_view(), name='api-logout'),
]
