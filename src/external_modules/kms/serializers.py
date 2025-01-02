from rest_framework import serializers

class UploadedFileSerializer(serializers.Serializer):
    file = serializers.FileField(upload_to='uploads/')
    uploaded_at = serializers.DateTimeField(auto_now_add=True)