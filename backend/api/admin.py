import traceback
from django import forms
from django.shortcuts import redirect, render
from django.urls import path 
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from rest_framework.request import Request
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from .views import upload_weight_csv
from .models import CustomUser, ExtractedImage, IProtectUser, WeightMeasurement


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
        'medewerker_number',
        'get_owner_username',
        'formatted_created_at'
    )
    search_fields = ('original_filename', 'user__username', 'medewerker_number')

    list_filter = (
        'image_type',
        'user',
        ('created_at', admin.DateFieldListFilter),  # Filter on date
    )

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

    def formatted_created_at(self, obj):
        return obj.created_at.strftime('%d-%m-%Y %H:%M') if obj.created_at else '-'

    formatted_created_at.short_description = 'Upload Datum'
    formatted_created_at.admin_order_field = 'created_at'


@admin.register(IProtectUser)
class IProtectUserAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email_name', 'ad_name', 'email_ns', 'email_eigen', 'has_ad', 'is_in_mail_dist')
    search_fields = ('full_name', 'email_name', 'ad_name', 'email_ns', 'email_eigen')
    list_filter = ('has_ad', 'is_in_mail_dist')


class CsvImportForm(forms.Form):
    csv_file = forms.FileField()


@admin.register(WeightMeasurement)
class WeightMeasurementAdmin(admin.ModelAdmin):
    list_display = ('date', 'weight_kg', 'bone_mass', 'body_fat', 'body_water', 'muscle_mass', 'bmi')
    change_list_template = "admin/weightmeasurement_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='api_weightmeasurement_import_csv'),
        ]
        return my_urls + urls

    @method_decorator(csrf_protect, name='dispatch')
    def import_csv(self, request):
        if request.method == "POST":
            form = CsvImportForm(request.POST, request.FILES)
            if form.is_valid():
                # Wrap Django request as DRF request with parsers
                drf_request = Request(request, parsers=[MultiPartParser(), FormParser()])
                drf_request.user = request.user  # Keep user for auth

                if response.status_code == status.HTTP_200_OK:
                    self.message_user(request, response.data.get('message', 'CSV imported'))
                else:
                    self.message_user(request, response.data.get('error', 'Error uploading csv'), level='error')

                return redirect('..')

        else:
            form = CsvImportForm()

        return render(request, 'admin/csv_form.html', {'form': form})

