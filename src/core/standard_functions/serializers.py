"""
Этот модуль содержит сериализаторы для Django-приложения.
"""

from rest_framework import serializers

class DatabaseConfigSerializer(serializers.Serializer):
    """
    Сериализатор для валидации и десериализации данных конфигурации базы данных.
    """

    database = serializers.CharField(max_length=100)
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=100)
    host = serializers.CharField(max_length=100)
    port = serializers.IntegerField()