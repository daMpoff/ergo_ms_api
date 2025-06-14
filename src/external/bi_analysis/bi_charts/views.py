from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Chart, Dataset
from .serializers import ChartSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .methods import fetch_columns_and_types, get_rows_for_chart
from rest_framework.views import APIView

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
    
class ChartRowsAPIView(APIView):
    def get(self, request, pk):
        rows = get_rows_for_chart(pk)
        return Response(rows)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dataset_columns(request, pk: int):
    ds = get_object_or_404(
        Dataset.objects.only('id', 'owner', 'table_ref'),
        pk=pk, owner=request.user
    )

    try:
        cols = fetch_columns_and_types(ds.table_ref)
    except Exception as exc:
        return Response(
            {"detail": f"Не удалось получить колонки: {exc}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({
        "dataset_id": pk,
        "columns": cols
    })