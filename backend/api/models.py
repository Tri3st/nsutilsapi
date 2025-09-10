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

