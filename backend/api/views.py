import os
import uuid
import datetime
import base64

from django.core.files.base import ContentFile
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import permission_classes, api_view, authentication_classes, parser_classes
from django.conf import settings
from django.http import JsonResponse
from PIL import Image, ImageDraw, ImageFont

from .serializers import ExtractedImageSerializer
from .authentication import BearerAuthentication
from .models import ExtractedImage
import xml.etree.ElementTree as ET

@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            user_info = {
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
            }
            return Response({
                'detail': 'Logged in succesfully',
                'userinfo': user_info,
            })
        else:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class UserInfoView(APIView):
    authentication_classes = [SessionAuthentication, BearerAuthentication]
    permissions_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_info = {
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
        return Response({"userinfo": user_info})


class LogoutView(APIView):
    authentication_classes = [SessionAuthentication, BearerAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'detail': 'Logged out succesfully'})


@authentication_classes([BearerAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
# @csrf_exempt  # remove if you handle CSRF tokens in Vue TEMPORARILY DISABLED FOR TESTING
def text_to_image(request):
    user = request.user

    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if not text:
            return JsonResponse({"error": "No text provided"}, status=400)

        # Create output dir if not exists
        output_dir = os.path.join(settings.MEDIA_ROOT, "rawimg")
        os.makedirs(output_dir, exist_ok=True)

        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.png"
        output_path = os.path.join(output_dir, filename)

        # Font + layout
        font = ImageFont.load_default()
        padding = 20
        lines = text.splitlines()
        max_width = max([font.getsize(line)[0] for line in lines] + [200])
        height = (font.getsize("hg")[1] + 5) * len(lines) + 2 * padding

        # Create image
        img = Image.new("RGB", (max_width + 2 * padding, height), "white")
        draw = ImageDraw.Draw(img)

        y = padding
        for line in lines:
            draw.text((padding, y), line, font=font, fill="black")
            y += font.getsize(line)[1] + 5

        # Save PNG
        img.save(output_path, "PNG")

        # Build URL
        image_url = settings.MEDIA_URL + f"rawimg/{filename}"
        return JsonResponse({"image_url": image_url})

    return JsonResponse({"error": "Invalid request"}, status=405)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def upload_fotos(request):
    file_obj = request.FILES.get('file')
    if not file_obj:
        return JsonResponse({"error": "No file provided"}, status=400)

    # IF the file is a .zip then unzip it with provided code
    # IF file is xml proceed with 2 ways:
    # 1 - normal
    # 2 - retail



    tree = ET.parse(file_obj)
    root = tree.getroot()

    saved_images = []

    for idx, foto_elem in enumerate(root.findall('.//foto')):
        raw_data = foto_elem.text.strip()
        try:
            img_bytes = base64.b64decode(raw_data, validate=True)
        except Exception:
            # Assume raw binary string
            img_bytes = raw_data.encode("utf-8")

        filename = f"{request.user.username}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{idx}.jpg"
        image_path = os.path.join("images", request.user.username, filename)

        extracted = ExtractedImage.objects.create(
            user=request.user,
            image=ContentFile(img_bytes, name=filename),
            original_filename=filename,
        )
        saved_images.append({
            "url": request.build_absolute_uri(extracted.image.url),
            "id": extracted.id,
        })

    # Instead of manually building JSON, serialize them
    serializer = ExtractedImageSerializer(saved_images, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def convert_raw_image(request):
    raw_data = request.FILES.get('raw_data')
    if not raw_data:
        return JsonResponse({"error": "No raw data provided"}, status=400)

    # ... decode + save as before ...

    serializer = ExtractedImageSerializer(extracted, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def save_selected_images(request):
    ids = request.data.get('ids', [])
    user = request.user

    if not isinstance(ids, list) or not ids:
        return JsonResponse({"error": "No valid IDs provided."}, status=400)

    # Filter images belonging to user and with provided IDs
    images_to_save = ExtractedImage.objects.filter(id__in=ids, user=user)

    # Implement your "save" logic here — e.g., mark as saved, move, or process them
    # For demonstration, let's just delete them (or do something else)
    count = images_to_save.count()
    images_to_save.delete()

    return Response({"message": f"Successfully saved {count} images."})

