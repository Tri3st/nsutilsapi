from django.urls import path
from . import views

app_name = "identity_checker"

urlpatterns = [
    path("identities/", views.IdentityListView.as_view(), name="identity-list"),
    path("upload/", views.UploadView.as_view(), name="upload"),
    path("cross-reference/", views.CrossReferenceView.as_view(), name="cross-reference"),
    path("upload-logs/", views.UploadLogView.as_view(), name="upload-logs"),
    path("status/", views.StatusView.as_view(), name="status"),
]
