from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Chart
from .serializers import ChartSerializer

class ChartListCreateView(generics.ListCreateAPIView):
    queryset = Chart.objects.all()
    serializer_class = ChartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ChartDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Chart.objects.all()
    serializer_class = ChartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=user)