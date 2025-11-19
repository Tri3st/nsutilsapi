import datetime
from django.utils import timezone

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('A', 'Admin'),
        ('U', 'User'),
        ('G', 'Guest'),
    )
    role = models.CharField(max_length=1, choices=ROLE_CHOICES)

    def __str__(self):
        return self.username


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/images_<username>/YYYY-MM-DD/filename
    date_str = instance.created_at.strftime('%Y-%m-%d') if instance.created_at else timezone.now().strftime('%Y-%m-%d')
    return f"images_{instance.user.username}_{date_str}/{filename}"


class ExtractedImage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='extracted_images'
    )
    medewerker_number = models.CharField(max_length=50)
    image = models.ImageField(upload_to=user_directory_path)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    image_type = models.CharField(max_length=10, blank=True, null=True)
    image_size = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.medewerker_number} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

    def delete(self, *args, **kwargs):
        """ Make sure we delete the image file when removing the row"""
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)


class BaseUser(models.Model):
    SOURCE_CHOICES = (
        ('iProtect', 'iProtect'),
        ('iWork', 'iWork'),
        ('OCMS', 'OCMS'),
    )
    full_name = models.CharField(max_length=255, blank=True, null=True)
    ad_name = models.CharField(max_length=255, blank=True, null=True)
    email_name = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    middle_names = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    initials = models.CharField(max_length=255, blank=True, null=True)
    email_eigen = models.EmailField(blank=True, null=True)
    email_ns = models.EmailField(blank=True, null=True)
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES)  # 'iprotect', 'iwork', 'ocms'
    has_ad = models.BooleanField(default=False)
    is_in_mail_dist = models.BooleanField(default=False)


    class Meta:
        abstract = True


class IProtectUser(BaseUser):
    # Add specific fields or flags if needed
    def __str__(self):
        return self.email_ns or self.email_eigen or "Unnamed user"


class IWorkUser(BaseUser):
    # Add specific fields or flags if needed
    def __str__(self):
        return self.email_ns or self.email_eigen or "Unnamed user"


class OCMSUser(BaseUser):
    # Add specific fields or flags if needed
    def __str__(self):
        return self.email_ns or self.email_eigen or "Unnamed user"

