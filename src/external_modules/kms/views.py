from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'file',
                openapi.IN_FORM,
                description="File to upload",
                type=openapi.TYPE_FILE
            )
        ],
        responses={201: "File uploaded successfully"}
    )
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')

        if file:
            file_path = default_storage.save('uploads/' + file.name, ContentFile(file.read()))
            return Response(
                {
                    "message": f"Файл успешно загружен: {file.name}.",
                    "file_path": file_path
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {
                    "error": "Файл не был загружен."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
