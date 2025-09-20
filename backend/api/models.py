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


class ExtractedImage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='extracted_images'
    )
    image = models.ImageField(upload_to=f"images_{user.username}_%Y-%m-%d")
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.created_at.at_strftime('%Y-%m-%d %H:%M:%S')}"