from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import base64
from django.contrib.auth import authenticate

class BearerAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            return None  # Continue with other authentication methods

        token = auth_header.split(' ', 1)[1]
        try:
            decoded = base64.b64decode(token).decode('utf-8')
            username, password = decoded.split(':', 1)
        except Exception:
            raise AuthenticationFailed('Invalid Bearer token')

        user = authenticate(username=username, password=password)
        if user is None:
            raise AuthenticationFailed("Invalid username/password")
        return (user, None)
