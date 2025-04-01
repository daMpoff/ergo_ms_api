from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from src.external.lms.models import Subject
import datetime

class Competence(models.Model):
    name = models.CharField(max_length=255, default='')

class Skill(models.Model):
    name =models.CharField(max_length=255, default='')

class Vacance (models.Model):
    name = models.CharField(max_length=255, default='')
    salary_from = models.FloatField(default=0)
    salary_to = models.FloatField(default=0)
    currency = models.CharField(max_length=255, default='')
    area = models.CharField(max_length=255, default='')
    type = models.CharField(max_length=255, default='')
    employment = models.CharField(max_length=255, default='')
    experience = models.CharField(max_length=255, default='')
    skill = models.ManyToManyField(Skill, related_name='vacance_skill')
    

class Skill_Course(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, default=0)
    sat_coef = models.FloatField(default=0)

class Competence_Course(models.Model):
    competence = models.ForeignKey(Competence, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, default=0)
    sat_coef = models.FloatField(default=0)