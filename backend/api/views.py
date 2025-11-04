import io
import os
import shutil
import uuid
import datetime
import base64
import zipfile

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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_info = {
            "username": user.username,
            "email": user.email,
            "role": getattr(user, "role", None),
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


def find_child_case_insensitive(elem, tag_candidate):
    """ Helper function to find a child element by tag name, ignoring case."""
    for child in elem:
        if child.tag.lower() == tag_candidate.lower():
            return child
    return None


@api_view(['POST'])
@ensure_csrf_cookie
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def upload_fotos(request):
    file_obj = request.FILES.get('file')
    zippassw = request.POST.get('zip-passw')
    xml_content = None

    if not file_obj:
        return JsonResponse({"error": "No file provided"}, status=400)

    # --- Handle ZIP uploads ---
    if file_obj.name.lower().endswith('.zip'):
        if not zippassw:
            return JsonResponse({"error": "ZIP password is required for ZIP files"}, status=400)

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp', str(uuid.uuid4()))
        os.makedirs(temp_dir, exist_ok=True)

        try:
            zip_path = os.path.join(temp_dir, file_obj.name)
            with open(zip_path, 'wb') as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)

            with zipfile.ZipFile(zip_path) as zf:
                try:
                    zf.extractall(path=temp_dir, pwd=zippassw.encode())
                except (zipfile.BadZipfile, RuntimeError):
                    return JsonResponse({"error": "Invalid ZIP file or wrong password"}, status=400)

            xml_files = [f for f in os.listdir(temp_dir) if f.lower().endswith('.xml')]
            if not xml_files:
                return JsonResponse({"error": "No XML file found in the ZIP archive"}, status=400)

            xml_path = os.path.join(temp_dir, xml_files[0])
            with open(xml_path, 'rb') as f:
                xml_content = f.read()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # --- Parse XML content ---
    if xml_content:
        tree = ET.parse(io.BytesIO(xml_content))
    else:
        tree = ET.parse(file_obj)
    root = tree.getroot()

    saved_images = []

    # --- Iterate through koppeling_medewerkers_fotos elements ---
    for koppeling_elem in root.iter():
        tag = koppeling_elem.tag.lower()
        if tag in ('koppeling_medewerker_fotos', 'koppeling_medewerkers_fotos'):
            medewerker_elem = find_child_case_insensitive(koppeling_elem, 'Medewerker')
            afbeelding_elem = find_child_case_insensitive(koppeling_elem, 'Afbeelding')

            if medewerker_elem is None or afbeelding_elem is None:
                continue

            medewerker_number = medewerker_elem.text.strip()
            raw_data = afbeelding_elem.text.strip()

            # Try to decode base64; fallback to raw binary
            try:
                img_bytes = base64.b64decode(raw_data, validate=True)
            except Exception:
                img_bytes = raw_data.encode('utf-8')

            # Detect image type by header bytes
            if img_bytes.startswith(b'\xff\xd8\xff'):
                image_type = 'jpg'
            elif img_bytes.startswith(b'\x89PNG'):
                image_type = 'png'
            else:
                image_type = 'jpg'

            image_size = len(img_bytes)
            filename = f"{request.user.username}_{medewerker_number}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{image_type}"

            extracted = ExtractedImage.objects.create(
                user=request.user,
                medewerker_number=medewerker_number,
                image=ContentFile(img_bytes, name=filename),
                original_filename=filename,
                image_type=image_type,
                image_size=image_size,
            )

            saved_images.append(extracted)

    serializer = ExtractedImageSerializer(saved_images, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def upload_foto(request):
    file_obj = request.FILES.get('file')
    image_type = request.POST.get('image_type')
    image_size = request.POST.get('image_size')

    if not file_obj:
        return JsonResponse({"error": "No file provided"}, status=400)

    if not image_type or not image_size:
        return JsonResponse({"error": "image_type and image_size are required"}, status=400)

    try:
        image_size = int(image_size)
    except ValueError:
        return JsonResponse({"error": "Invalid image_size"}, status=400)

    original_filename = file_obj.name

    # Use the filename as-is (trusting frontend)
    filename_to_save = original_filename

    # Save image content
    img_bytes = file_obj.read()

    extracted = ExtractedImage.objects.create(
        user=request.user,
        medewerker_number='',
        image=ContentFile(img_bytes, name=filename_to_save),
        original_filename=original_filename,
        image_type=image_type,
        image_size=image_size,
    )

    serializer = ExtractedImageSerializer(extracted, context={'request': request})

    return JsonResponse(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_uploaded_fotos(request):

    user = request.user
    if user.role == 'A':
        # Admin: list all images with owner's username
        queryset = ExtractedImage.objects.select_related('user').all()
    else:
        # Regular user: only own images
        queryset = ExtractedImage.objects.filter(user=user)

    serializer = ExtractedImageSerializer(queryset, many=True, contect={'request': request})

    # For admin include the username in the response (if not in serializer, extend it)
    if user.role == 'A':
        # add username manually if not present on serializer
        data = serializer.data
        for item, obj in zip(data, queryset):
            item['owner_username'] = obj.user.username
        return JsonResponse(data)

    return JsonResponse(serializer.data)
