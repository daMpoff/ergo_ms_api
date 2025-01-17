from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from src.external.lms.scripts import get_courses

class CoursesView(APIView):
    def get(self, request, *args, **kwargs):
        data = get_courses(10, 10, 10)
        return Response(data, status=status.HTTP_200_OK)