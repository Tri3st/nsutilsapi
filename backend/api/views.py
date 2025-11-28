import io
import os
import shutil
import uuid
import datetime
import base64
import zipfile
import csv
import logging

from io import TextIOWrapper
from django.core.files.base import ContentFile
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework import status
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import parser_classes
from django.conf import settings
from django.http import JsonResponse
from PIL import Image, ImageDraw, ImageFont
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
import xml.etree.ElementTree as ET

from .serializers import ExtractedImageSerializer, WeightMeasurementsSerializer
from .authentication import BearerAuthentication
from .models import ExtractedImage, WeightMeasurement


logger = logging.getLogger('api')

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
    paginator = PageNumberPagination()
    paginator.page_size = 12  # Adjust if needed

    if user.role == 'A':
        # Admin: list all images with owner's username
        queryset = ExtractedImage.objects.select_related('user').order_by('-created_at')
    else:
        # Regular user: only own images
        queryset = ExtractedImage.objects.filter(user=user).order_by('-created_at')

    paginated_qs = paginator.paginate_queryset(queryset, request)
    serializer = ExtractedImageSerializer(paginated_qs, many=True, context={'request': request})

    # For admin include the username in the response (if not in serializer, extend it)
    if user.role == 'A':
        # add username manually if not present on serializer
        data = serializer.data
        for item, obj in zip(data, queryset):
            item['owner_username'] = obj.user.username
        return paginator.get_paginated_response(data)

    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_weight_csv(request):

    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'error': 'No file uploaded.'}, status=400)

    csv_file = TextIOWrapper(file_obj.file, encoding='utf-8')

    # Skip the first 9 metadata lines
    for _ in range(9):
        next(csv_file)

    reader = csv.DictReader(csv_file, delimiter=";")

    # Find the latest datetime in DB
    latest_entry = WeightMeasurement.objects.order_by('-date').first()
    latest_datetime = latest_entry.date if latest_entry else None

    count = 0
    errors = 0

    logger.info(f"Latest WeightMeasurement date in DB: {latest_datetime}")

    for row in reader:
        try:
            datetime_str = row['Date - Time'].strip()
            dt = datetime.datetime.strptime(datetime_str, '%m/%d/%Y - %H:%M')

            # If no entries in DB, import all rows
            if latest_datetime and dt <= latest_datetime:
                logger.info(f"Skipping row with date {dt} because its <= latest DB date {latest_datetime}")
                continue

            weight = float(row['Body weight (kg)'].strip())
            bone_mass = float(row.get('Bone mass (%)').strip() or 0)
            body_fat = float(row.get('Body fat (%)').strip() or 0)
            body_water = float(row.get('Body water (%)').strip() or 0)
            muscle_mass = float(row.get('Muscle mass (%)').strip() or 0)
            bmi = float(row.get('BMI').strip() or 0)

            WeightMeasurement.objects.update_or_create(
                date=dt,
                defaults={
                    'weight_kg': weight,
                    'bone_mass': bone_mass,
                    'body_fat': body_fat,
                    'body_water': body_water,
                    'muscle_mass': muscle_mass,
                    'bmi': bmi,
                }
            )
            count += 1
        except Exception as e:
            errors += 1
            logger.error(f"Error processing CSV row {row}: {e}", exc_info=True)

    return Response({
        'message': f'Successfully processed {count} entries.',
        'errors': errors
    })


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def weight_measurement_list(request):

    user = request.user

    queryset = WeightMeasurement.objects.filter(user=user).order_by('date')

    # Filtering
    date_gte = request.GET.get('date__gte')
    date_lte = request.GET.get('date__lte')
    if date_gte:
        queryset = queryset.filter(date__gte=date_gte)
    if date_lte:
        queryset = queryset.filter(date__lte=date_lte)

    # Ordering
    ordering = request.GET.get('ordering')
    if ordering in ['date', '-date', 'weight_kg', '-weight_kg']:
        queryset = queryset.order_by(ordering)

    # Use the project's global paginator
    paginator = PageNumberPagination()  # DRF will inject DEFAULT_PAGINATION_CLASS settings
    paginated_page = paginator.paginate_queryset(queryset, request)

    serializer = WeightMeasurementsSerializer(paginated_page, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def latest_measurement_datetime(request):
    latest = WeightMeasurement.objects.order_by('-date').first()
    if latest:
        return Response({'date': latest.datetime.isoformat()})
    return Response({'date': None})


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_minmaxavg(request):
    user = request.user

    # get min, max and avg values for all the values of this user
    total = {
        'count': 0,
        'weight_kg': 0,
        'bone_mass': 0,
        'body_fat': 0,
        'body_water': 0,
        'muscle_mass': 0,
        'bmi': 0
    }
    min = {
        'weight_kg': 1000,
        'bone_mass': 100,
        'body_fat': 100,
        'body_water': 100,
        'muscle_mass': 100,
        'bmi': 1000
    }
    max = {
        'weight_kg': 0,
        'bone_mass': 0,
        'body_fat': 0,
        'body_water': 0,
        'muscle_mass': 0,
        'bmi': 0
    }
    measurements = WeightMeasurement.objects.filter(user=user)
    for measurement in measurements:
        for key in total.keys():
            if key != 'count':
                total[key] += getattr(measurement, key)
                if getattr(measurement, key) < min[key]:
                    min[key] = getattr(measurement, key)
                if getattr(measurement, key) > max[key]:
                    max[key] = getattr(measurement, key)
            total['count'] += 1

    print(total)
    if total['count'] == 0:
        return Response({'error': 'No measurements found for this user.'})

    results = {
        'avg': {
            'weight_kg': total['weight_kg']/total['count'],
            'bone_mass': total['bone_mass']/total['count'],
            'body_fat': total['body_fat']/total['count'],
            'body_water': total['body_water']/total['count'],
            'muscle_mass': total['muscle_mass']/total['count'],
            'bmi': total['bmi']/total['count']
        },
        'min': {
            'weight_kg': min['weight_kg'],
            'bone_mass': min['bone_mass'],
            'body_fat': min['body_fat'],
            'body_water': min['body_water'],
            'muscle_mass': min['muscle_mass'],
            'bmi': min['bmi']
        },
        'max': {
            'weight_kg': max['weight_kg'],
            'bone_mass': max['bone_mass'],
            'body_fat': max['body_fat'],
            'body_water': max['body_water'],
            'muscle_mass': max['muscle_mass'],
            'bmi': max['bmi']
        }
    }
    return Response({'minmaxavg': results})
