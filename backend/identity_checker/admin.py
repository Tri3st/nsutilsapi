from django.contrib import admin
from .models import Identity, UploadLog


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = ("username", "application", "source", "email", "display_name", "department", "uploaded_at")
    list_filter = ("application", "source")
    search_fields = ("username", "email", "display_name", "department")
    ordering = ("application", "source", "username")
    readonly_fields = ("uploaded_at", "extra_data")

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("application", "source", "username")


@admin.register(UploadLog)
class UploadLogAdmin(admin.ModelAdmin):
    list_display = ("filename", "application", "source", "row_count", "status", "uploaded_at")
    list_filter = ("application", "source", "status")
    search_fields = ("filename",)
    readonly_fields = ("application", "source", "filename", "row_count", "uploaded_at", "status", "error_message")
    ordering = ("-uploaded_at",)

    def has_add_permission(self, request):
        return False
