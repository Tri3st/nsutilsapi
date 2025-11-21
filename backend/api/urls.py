from django.urls import path
from .views import (text_to_image, LoginView, LogoutView, upload_foto,
                    upload_fotos, UserInfoView, list_uploaded_fotos, weight_measurement_list,
                    upload_weight_csv, latest_measurement_datetime)

urlpatterns = [
    path("text-to-image/", text_to_image, name="text_to_image"),
    path('upload-foto/', upload_foto, name="upload_foto"),
    path('upload-fotos/', upload_fotos, name="upload_fotos"),
    path('list_uploaded_fotos/', list_uploaded_fotos, name="list_uploaded_fotos"),
    path('upload-csv/', upload_weight_csv, name='upload-weight-csv'),
    path('weight-data/', weight_measurement_list, name='userinfo'),
    path('latest-datetime/', latest_measurement_datetime, name='latest-datetime'),
    path('userinfo/', UserInfoView.as_view(), name='userinfo'),
    path('login/', LoginView.as_view(), name='api-login'),
    path('logout/', LogoutView.as_view(), name='api-logout'),
]
