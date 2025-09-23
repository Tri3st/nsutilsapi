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
    image = models.ImageField(upload_to=user_directory_path)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.created_at.at_strftime('%Y-%m-%d %H:%M:%S')}"
