from rest_framework import serializers

class DatabaseConfigSerializer(serializers.Serializer):
    database = serializers.CharField(max_length=100)
    username = serializers.CharField(max_length=100)
    password = serializers.CharField(max_length=100)
    host = serializers.CharField(max_length=100)
    port = serializers.IntegerField()

class ScriptSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=['py', 'js', 'rb', 'cpp', 'cs', 'php'])
    code = serializers.CharField()