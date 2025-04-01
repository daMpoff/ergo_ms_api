from django.db import models
from django.contrib.auth.models import User
import datetime
class Subject(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=datetime.date.today())
    lastupdate = models.DateTimeField(default=datetime.datetime.now())
    teacher = models.ForeignKey(User, on_delete= models.CASCADE)

class Grade(models.Model):
    subject = models.ForeignKey(Subject, on_delete= models.CASCADE, default=0)
    related = models.DateField(default=datetime.date.today())
    lastupdate = models.DateTimeField(default=datetime.datetime.now())
    student = models.ForeignKey(User, on_delete= models.CASCADE)
    grade = models.IntegerField( default=0)

class Theme(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=datetime.datetime.now())
    lastupdate = models.DateTimeField(default=datetime.datetime.now())
    subject = models.ForeignKey(Subject, on_delete= models.CASCADE, default=0)

class Lesson(models.Model):
    class LessonType(models.TextChoices):
        video = 'V'
        conference ='C'
        lecture = 'L'
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=datetime.date.today())
    lastupdate = models.DateTimeField(default=datetime.datetime.now())
    lessontype = models.CharField(max_length=40,choices=LessonType.choices, default=LessonType.lecture)
    content = models.BinaryField (default=b'\x08')
    theme = models.ForeignKey(Theme, on_delete= models.CASCADE)

class Test(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=datetime.date.today())
    lastupdate = models.DateTimeField(default=datetime.datetime.now())
    lesson = models.ForeignKey(Lesson, on_delete= models.CASCADE)
    timelimit = models.IntegerField(default=0)
    class TestType(models.TextChoices):
        close = 'C'
        game = 'G'
        open = 'O'
    type = models.CharField(max_length=100,choices=TestType, default= TestType.close)   
    title = models.CharField(max_length=255, default='')

class Question(models.Model):
    text= models.TextField(default='')
    points = models.IntegerField(default=0)
    lastupdate = models.DateTimeField(default=datetime.datetime.now())
    correctanswer = models.TextField(default='')
    class QuestionType(models.TextChoices):
        single = 'S'
        open = 'O'
    type = models.CharField(max_length=100, choices=QuestionType, default=QuestionType.single)
    test = models.ForeignKey(Test, on_delete= models.CASCADE)

class UserAnswer(models.Model):
    answer = models.TextField(default='')
    iscorrect = models.BooleanField(default=False)
    Student = models.ForeignKey(User, on_delete= models.CASCADE)
    Question = models.ForeignKey(Question, on_delete= models.CASCADE)

class Assignment(models.Model):
    title = models.CharField(max_length=255, default='')
    description = models.TextField(default='')
    deadline = models.DateField(default=datetime.date.today())
    creationdate = models.DateField(default=datetime.date.today())
    lastupdate = models.DateTimeField(default=datetime.datetime.now())
    lesson = models.ForeignKey(Lesson, on_delete= models.CASCADE)

class SubmittedAssignment(models.Model):
    submittedassignment = models.BinaryField(default=b'\x08')
    comment = models.TextField(default='')
    grade = models.IntegerField(default=0)
    dateofsubmit = models.DateField(default=datetime.date.today())
    Student = models.ForeignKey(User, on_delete= models.CASCADE)
    Assignment = models.ForeignKey(Assignment, on_delete= models.CASCADE)
