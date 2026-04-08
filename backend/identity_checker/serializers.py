from rest_framework import serializers
from .models import Identity, UploadLog


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Identity
        fields = [
            "id",
            "application",
            "source",
            "username",
            "email",
            "display_name",
            "department",
            "extra_data",
            "uploaded_at",
        ]


class UploadLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadLog
        fields = [
            "id",
            "application",
            "source",
            "filename",
            "row_count",
            "uploaded_at",
            "status",
            "error_message",
        ]
