import logging
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
from rest_framework.status import HTTP_200_OK
from rest_framework import status
from .views import upload_weight_csv
from .models import CustomUser, ExtractedImage, IProtectUser, WeightMeasurement


# Use the api logger
logger = logging.getLogger('api')


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
    csv_file = forms.FileField(label='CSV file')


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
                csv_file = form.cleaned_data['csv_file']
                logger.info("CSV upload started by user %s via admin view.", request.user)

                
                # Wrap Django request as DRF request with parsers
                drf_request = Request(request, parsers=[MultiPartParser(), FormParser()])
                drf_request.user = request.user  # Keep user for auth

                # IMPORTANT: The DRF view expects the file in request.FILES['file']
                # So override FILES to rename 'csv_file' to 'file'
                drf_request.FILES._mutable = True
                drf_request.FILES['file'] = csv_file

                if 'csv_file' in drf_request.FILES:
                    del drf_request.FILES['csv_file']
                drf_request.FILES._mutable = False

                try:
                    # Call your exeisting DRF View functionm
                    response = upload_weight_csv(drf_request._request)  # Pass orginal request

                    if response.status_code == status.HTTP_200_OK:
                        message = response.data.get('message', 'CSV imported successfully.')
                        self.message_user(request, message)
                        logger.info("User %s successfully imported CSV, message is: %s", request.user, message)
                    else:
                        err_msg = response.data.get('error', 'Error uploading csv')
                        self.message_user(request, err_msg, level="error")
                        logger.error("User %s CSV import failed, error: %s", request.user, err_msg)

                    return redirect('..')

                except Excpetion as e:
                    logger.error("User %s encountered an exception during csv import: %s", request.user, e, exc_info=True)
                    self.message_user(request, f"Unexpected error: {e}", level="error")

        else:
            form = CsvImportForm()

        return render(request, 'admin/csv_form.html', {'form': form})

