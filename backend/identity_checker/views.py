from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError

from .models import Identity, UploadLog, Application, IdentitySource
from .serializers import IdentitySerializer, UploadLogSerializer
from .parsers import parse_file
from .cross_reference import cross_reference


class IdentityListView(APIView):
    """
    GET /api/identity-checker/identities/?application=iprotect&source=users
    DELETE /api/identity-checker/identities/?application=iprotect&source=users
    """

    def get(self, request):
        application = request.query_params.get("application")
        source = request.query_params.get("source")

        qs = Identity.objects.all()
        if application:
            qs = qs.filter(application=application)
        if source:
            qs = qs.filter(source=source)

        serializer = IdentitySerializer(qs, many=True)
        return Response(serializer.data)

    def delete(self, request):
        application = request.query_params.get("application")
        source = request.query_params.get("source")

        if not application or not source:
            return Response(
                {"error": "application and source are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = Identity.objects.filter(
            application=application, source=source
        ).delete()

        return Response({"deleted": deleted_count})


class UploadView(APIView):
    """
    POST /api/identity-checker/upload/
    Form data: application, source, file
    Replaces all existing identities for that application+source.
    """

    def post(self, request):
        application = request.data.get("application")
        source = request.data.get("source")
        file = request.FILES.get("file")

        # Validate
        if not application or application not in Application.values:
            return Response(
                {"error": f"Invalid application. Choose from: {Application.values}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not source or source not in IdentitySource.values:
            return Response(
                {"error": f"Invalid source. Choose from: {IdentitySource.values}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not file:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filename = file.name
        if not (filename.endswith(".csv") or filename.endswith(".xlsx") or filename.endswith(".xls")):
            return Response(
                {"error": "Only .csv and .xlsx files are supported"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rows = parse_file(file, filename)
        except Exception as e:
            UploadLog.objects.create(
                application=application,
                source=source,
                filename=filename,
                row_count=0,
                status="error",
                error_message=str(e),
            )
            return Response({"error": f"Parse error: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        if not rows:
            return Response({"error": "File is empty or has no data rows"}, status=status.HTTP_400_BAD_REQUEST)

        # Check we have at least a username column
        if not any(r.get("username") for r in rows):
            return Response(
                {"error": "Could not find a username/user/login column in the file"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Replace existing data
        Identity.objects.filter(application=application, source=source).delete()

        created = 0
        skipped = 0
        for row in rows:
            username = row.get("username", "").strip()
            if not username:
                skipped += 1
                continue
            try:
                Identity.objects.create(
                    application=application,
                    source=source,
                    username=username,
                    email=row.get("email"),
                    display_name=row.get("display_name"),
                    department=row.get("department"),
                    extra_data=row.get("extra_data", {}),
                )
                created += 1
            except IntegrityError:
                skipped += 1

        UploadLog.objects.create(
            application=application,
            source=source,
            filename=filename,
            row_count=created,
            status="success",
        )

        return Response({
            "application": application,
            "source": source,
            "filename": filename,
            "created": created,
            "skipped": skipped,
        }, status=status.HTTP_201_CREATED)


class CrossReferenceView(APIView):
    """
    GET /api/identity-checker/cross-reference/?application=iprotect
    """

    def get(self, request):
        application = request.query_params.get("application")

        if not application or application not in Application.values:
            return Response(
                {"error": f"Invalid application. Choose from: {Application.values}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = cross_reference(application)
        return Response(result)


class UploadLogView(APIView):
    """
    GET /api/identity-checker/upload-logs/?application=iprotect
    """

    def get(self, request):
        application = request.query_params.get("application")
        qs = UploadLog.objects.all()
        if application:
            qs = qs.filter(application=application)
        serializer = UploadLogSerializer(qs[:50], many=True)
        return Response(serializer.data)


class StatusView(APIView):
    """
    GET /api/identity-checker/status/
    Returns which application+source combinations have data loaded.
    """

    def get(self, request):
        result = {}
        for app in Application.values:
            result[app] = {}
            for src in IdentitySource.values:
                count = Identity.objects.filter(application=app, source=src).count()
                result[app][src] = count

        return Response(result)

