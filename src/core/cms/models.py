from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Tag(models.Model):
    name = models.CharField(max_length=100, default='')

class Category(models.Model):
    name = models.CharField(max_length=100, default='')
    parentcategory = models.ForeignKey('self', on_delete=models.PROTECT)

class Object_Type(models.Model):
    name = models.CharField(max_length=100, default='')

class Object(models.Model):
    objectlink = models.CharField(max_length=255, default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.ForeignKey(Object_Type, on_delete=models.CASCADE)