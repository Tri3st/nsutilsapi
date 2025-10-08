# backend/api/serializer.py
from rest_framework import serializers
from .models import ExtractedImage


class ExtractedImageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ExtractedImage
        fields = [
            "id",
            "username",
            "role",
            "image",
            "url",
            "original_filename",
            "created_at",
        ]

    def get_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

