from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    
class StudentGroup(models.Model):
    name = models.CharField(max_length=255, default='')
    curator = models.ForeignKey(Teacher, on_delete=models.CASCADE)

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE)


class Subject(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-creationdate']


class Grade(models.Model):
    subject = models.ForeignKey(Subject, on_delete= models.CASCADE, default=0)
    related = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    student = models.ForeignKey(User, on_delete= models.CASCADE)
    grade = models.IntegerField( default=0)

class Theme(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    subject = models.ForeignKey(Subject, on_delete= models.CASCADE, default=0)

class Lesson(models.Model):
    class LessonType(models.TextChoices):
        video = 'V'
        conference ='C'
        lecture = 'L'
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    lessontype = models.CharField(max_length=40,choices=LessonType.choices, default=LessonType.lecture)
    content = models.BinaryField (default=b'\x08')
    theme = models.ForeignKey(Theme, on_delete= models.CASCADE)

class TestBank(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='test_banks')

    def __str__(self):
        return self.name

class Test(models.Model):
    name = models.CharField(max_length=100, default='')
    description = models.TextField(default='')
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    timelimit = models.IntegerField(default=0)
    class TestType(models.TextChoices):
        close = 'C'
        game = 'G'
        open = 'O'
    type = models.CharField(max_length=100,choices=TestType, default= TestType.close)   
    title = models.CharField(max_length=255, default='')
    test_bank = models.ForeignKey(TestBank, on_delete=models.CASCADE, related_name='tests', null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    passing_score = models.IntegerField(default=70)
    is_active = models.BooleanField(default=True)


class Question(models.Model):
    text = models.TextField(default='')
    points = models.IntegerField(default=0)
    lastupdate = models.DateTimeField(default=timezone.now)
    correctanswer = models.TextField(default='')
    class QuestionType(models.TextChoices):
        single = 'S'
        open = 'O'
        multiple = 'M'
    type = models.CharField(max_length=100, choices=QuestionType, default=QuestionType.single)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    test_bank = models.ForeignKey(TestBank, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.text[:50]}..."

class TestAttempt(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    is_passed = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=20, default='in_progress')

    def __str__(self):
        return f"{self.student.username} - {self.test.title}"

    def calculate_score(self):
        """Calculate the score as a percentage"""
        total_points = 0
        earned_points = 0
        
        for answer in self.answers.all():
            question = answer.question
            total_points += question.points
            
            if answer.is_correct:
                earned_points += question.points
        
        if total_points > 0:
            return (earned_points / total_points) * 100
        return 0

class StudentAnswer(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Answer for {self.question.text[:50]}..."

    def check_correctness(self):
        """Check if the answer is correct"""
        if self.question.type == 'S':  # Single choice
            correct_answer = self.question.answers.filter(is_correct=True).first()
            selected_answer = self.selections.first()
            self.is_correct = selected_answer and selected_answer.answer == correct_answer
        elif self.question.type == 'M':  # Multiple choice
            correct_answers = set(self.question.answers.filter(is_correct=True))
            selected_answers = set(selection.answer for selection in self.selections.all())
            self.is_correct = correct_answers == selected_answers
        elif self.question.type == 'O':  # Open answer
            self.is_correct = self.text_answer.strip().lower() == self.question.correctanswer.strip().lower()
        self.save()

class StudentAnswerSelection(models.Model):
    student_answer = models.ForeignKey(StudentAnswer, on_delete=models.CASCADE, related_name='selections')
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Selection for {self.answer.text[:50]}..."

class UserAnswer(models.Model):
    answer = models.TextField(default='')
    iscorrect = models.BooleanField(default=False)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)


class Assignment(models.Model):
    title = models.CharField(max_length=255, default='')
    description = models.TextField(default='')
    deadline = models.DateField(default=timezone.now)
    creationdate = models.DateField(default=timezone.now)
    lastupdate = models.DateTimeField(default=timezone.now)
    lesson = models.ForeignKey(Lesson, on_delete= models.CASCADE)

class SubmittedAssignment(models.Model):
    submittedassignment = models.BinaryField(default=b'\x08')
    comment = models.TextField(default='')
    grade = models.IntegerField(default=0)
    dateofsubmit = models.DateField(default=timezone.now)
    student = models.ForeignKey(User, on_delete= models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete= models.CASCADE)
