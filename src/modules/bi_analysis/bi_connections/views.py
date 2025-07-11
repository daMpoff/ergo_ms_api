from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from src.modules.bi_analysis.bi_connections.models import Connection
from src.modules.bi_analysis.bi_connections.serializers import ConnectionSerializer
from src.modules.bi_analysis.bi_connections.methods import CheckConnection

from django.shortcuts import get_object_or_404
from sqlalchemy import create_engine, text

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
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class ConnectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        if obj.owner != self.request.user:
            raise PermissionDenied('У вас нет доступа к этому подключению')
        return obj
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            # Для генерации схемы Swagger возвращаем пустой queryset
            return Connection.objects.none()
        return Connection.objects.filter(owner=self.request.user)
    
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
        
class ConnectionTablesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, connection_id):
        connection = get_object_or_404(Connection, id=connection_id, owner=request.user)
        db_type = (connection.connector_type or "").lower().strip()

        try:
            if db_type == "postgresql":
                return Response(self._get_postgresql_tables(connection))
            elif db_type in ["mssql", "sql server"]:
                return Response(self._get_mssql_tables(connection))
            elif db_type == "clickhouse":
                return Response(self._get_clickhouse_tables(connection))
            else:
                raise ValidationError(f"Тип СУБД не поддерживается: {db_type}")
        except Exception as e:
            raise ValidationError(f"Ошибка при получении таблиц: {str(e)}")

    def _get_postgresql_tables(self, connection):
        cfg = connection.config
        user = cfg.get("user")
        password = cfg.get("password")
        host = cfg.get("host")
        port = cfg.get("port", 5432)
        db = cfg.get("database")

        url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')"
            ))
            return [{"name": row.table_name, "schema": row.table_schema} for row in result]

    def _get_mssql_tables(self, connection):
        cfg = connection.config
        user = cfg.get("user")
        password = cfg.get("password")
        host = cfg.get("host")
        port = cfg.get("port", 1433)
        db = cfg.get("database")

        url = f"mssql+pyodbc://{user}:{password}@{host},{port}/{db}?driver=ODBC+Driver+17+for+SQL+Server"
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
            ))
            return [{"name": row.TABLE_NAME, "schema": row.TABLE_SCHEMA} for row in result]

    def _get_clickhouse_tables(self, connection):
        import clickhouse_connect
        cfg = connection.config
        client = clickhouse_connect.get_client(
            host=cfg.get("host"),
            port=int(cfg.get("port", 8443)),
            username=cfg.get("user"),
            password=cfg.get("password"),
            database=cfg.get("database")
        )
        result = client.query("SHOW TABLES")
        return [{"name": row[0], "schema": cfg.get("database")} for row in result.result_rows]