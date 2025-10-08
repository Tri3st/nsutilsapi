# backend/api/serializer.py
from rest_framework import serializers
from .models import ExtractedImage


class ExtractedImageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = ExtractedImage
        fields = [
            "id",
            "username",
            "role",
            "medewerker_number",
            "image",
            "url",
            "original_filename",
            "image_type",
            "image_size",
            "created_at",
        ]

    def get_url(self, obj):
        """
        Return the absolute URL for the image file.
        """
        request = self.context.get("request")
        if obj.image and hasattr(obj.image, "url"):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

