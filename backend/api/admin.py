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
    list_display = UserAdmin.list_display + ('role',)  # Voeg role toe aan de lijstweergave

admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(ExtractedImage)
class ExtractedImageAdmin(admin.ModelAdmin):
    list_display = (
        'original_filename', 
        'image_preview', 
        'image_type', 
        'image_size', 
        'get_owner_username',
        'created_at'
    )
    search_fields = ('original_filename', 'owner_username')

    def image_preview(self, obj):
        try:
            if obj.image and obj.image.url:
                return format_html('<img src="{}" width="100" />', obj.image.url)
        except ValueError:
            pass
        return '-'

    image_preview.short_description = 'Preview'

    def get_owner_username(self, obj):
        return obj.user.username

    get_owner_username.short_description = 'Owner Username'
    get_owner_username.admin_order_field = 'user__username'

