from django.db import models
from django.contrib.auth.models import (User, Group, Permission)
from src.core.cms.models import (ExpandedPermission,Accession, GroupCategory, ExpandedGroup, PermissionMark, Accession)
from django.utils import timezone


def GetUserExpandedPermissions(user:User):
    groups = user.groups.all()
    expadedpermissions = []
    perms = user.user_permissions.all()
    for group in groups:
        permissions = group.permissions.all()
        for permission in permissions:
            exp = ExpandedPermission.objects.get(permission = permission)
            expadedpermissions.append(exp)
    for perm in perms:
        exp = ExpandedPermission.objects.get(permission = perm)
        expadedpermissions.append(exp)
        expadedpermissions = list(set(expadedpermissions))
    return expadedpermissions
