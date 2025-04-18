from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Connection
from .serializers import ConnectionSerializer

class ConnectionListCreateView(generics.ListCreateAPIView):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class ConnectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=user)