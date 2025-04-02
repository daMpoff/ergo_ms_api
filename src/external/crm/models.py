from django.db import models
from django.contrib.auth.models import User
import datetime

class Project(models.Model):
    name = models.CharField(max_length=100, default='')
    dateofcreation = models.DateField(default= datetime.date.today)
    creator = models.ForeignKey(User, on_delete= models.CASCADE)

class User_Project(models.Model):
    project = models.ForeignKey(Project, on_delete= models.CASCADE)
    user = models.ForeignKey(User, on_delete= models.CASCADE)
    isnew = models.BooleanField(default=True)

class Section(models.Model):
    name = models.CharField(max_length=100, default='')
    Project = models.ForeignKey(Project, on_delete= models.CASCADE)

class Task(models.Model):
    text = models.TextField(default="")
    isdone = models.BooleanField(default=False)
    description = models.TextField(default="")
    dateofcreation = models.DateField(default= datetime.date.today)
    deadline = models.DateField(default= datetime.date.today)
    priority = models.IntegerField(default=0)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    parenttask = models.ForeignKey('self', on_delete= models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class Calendar (models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(default='')
    time = models.DateTimeField(default= datetime.datetime.now())