from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Connection
from .serializers import ConnectionSerializer
from .methods import CheckConnection

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

    def get_object(self):
        obj = super().get_object()
        if obj.owner != self.request.user:
            raise PermissionDenied('У вас нет доступа к этому подключению')
        return obj
    
class CheckConnectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        db_type = request.data.get('type')
        host = request.data.get('host')
        port = request.data.get('port')
        username = request.data.get('username')
        password = request.data.get('password')
        database = request.data.get('database', 'default')

        try:
            if db_type == 'clickhouse':
                success, message = CheckConnection.check_clickhouse(host, port, username, password)
            elif db_type == 'postgresql':
                success, message = CheckConnection.check_postgresql(host, port, username, password, database)
            elif db_type == 'mssql':
                success, message = CheckConnection.check_mssql(host, port, username, password, database)
            else:
                return Response({'success': False, 'message': 'Тип базы данных не поддерживается'}, status=400)

            return Response({'success': success, 'message': message})

        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=400)