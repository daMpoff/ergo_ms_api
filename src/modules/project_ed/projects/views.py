from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ProjectCreateSerializer, ProjectReadSerializer


class ProjectCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ProjectCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        return Response(ProjectReadSerializer(project).data, status=status.HTTP_201_CREATED)