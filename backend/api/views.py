import os
import uuid
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageDraw, ImageFont


def check_bearer_auth(request):
    """
    Validates Bearer token that encodes 'username:password' in Base64.
    Returns Django user object if valid, otherwise None.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startsWith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]  # get part after "Bearer "
    try:
        decoded = base64.b64decode(token).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return None

    user = authenticate(username=username, password=password)
    return user


@csrf_exempt  # remove if you handle CSRF tokens in Vue
def text_to_image(request):
    user = check_bearer_auth(request)
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

