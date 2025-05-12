from django.db import models
from django.contrib.auth.models import (User, Group, Permission)
from django.utils import timezone

class Review(models.Model):
    author_id = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(default='')
    rating = models.IntegerField(default=0)

class GroupURL(models.Model):
    url = models.CharField(max_length=255, default='')
    group_id = models.ForeignKey(Group, on_delete=models.CASCADE)

class PermissionMark(models.Model):
    name = models.CharField(max_length=255, default='')

class GroupCategory(models.Model):
    name = models.CharField(max_length=255, default='')

class ExpandedPermission(models.Model):
    permission = models.OneToOneField(Permission, on_delete=models.CASCADE)
    permission_mark = models.ForeignKey(PermissionMark, on_delete=models.CASCADE)
    group_category = models.ForeignKey(GroupCategory, on_delete=models.CASCADE)

class Accession(models.Model):
    typeaccession = models.CharField(max_length=100, default='PageAccession')
    path = models.CharField(max_length=255, default='')
    component_id = models.CharField(max_length=255, default='')
    permission = models.OneToOneField(ExpandedPermission, on_delete=models.CASCADE, default=0)

class ExpandedGroup(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    category = models.ForeignKey(GroupCategory, on_delete=models.CASCADE)
    level = models.IntegerField(default=0)
