from django.db import models


class Application(models.TextChoices):
    IPROTECT = "iprotect", "iProtect"
    IWORK = "iwork", "iWork"
    OCMS = "ocms", "OCMS"


class IdentitySource(models.TextChoices):
    USERS = "users", "Users"
    MAIL_DIST_LIST = "mail_dist_list", "Mail Distribution List"
    AD_GROUP = "ad_group", "AD Group"


class Identity(models.Model):
    application = models.CharField(max_length=20, choices=Application.choices)
    source = models.CharField(max_length=20, choices=IdentitySource.choices)
    username = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    extra_data = models.JSONField(default=dict, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("application", "source", "username")
        indexes = [
            models.Index(fields=["application", "source"]),
        ]
        ordering = ["username"]

    def __str__(self):
        return f"{self.application} / {self.source} / {self.username}"


class UploadLog(models.Model):
    application = models.CharField(max_length=20, choices=Application.choices)
    source = models.CharField(max_length=20, choices=IdentitySource.choices)
    filename = models.CharField(max_length=255)
    row_count = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="success")
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.application}/{self.source} — {self.filename} ({self.uploaded_at:%Y-%m-%d %H:%M})"
