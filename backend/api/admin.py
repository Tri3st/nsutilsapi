from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, ExtractedImage


# Register your models here.
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    add_fieldset = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(ExtractedImage)
class ExtractedImageAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'image_type', 'imaige_size', 'owner_username')
    search_fields = ('original_filename', 'owner_username')

    def image_preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" width="100" />', obj.url)
        return '-'
    image_preview.short_description = 'Preview'

