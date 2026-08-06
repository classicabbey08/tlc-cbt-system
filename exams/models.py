from django.conf import settings
from django.db import models

from accounts.models import User


class Subject(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Exam(models.Model):
    """
    A CBT: a timed set of questions under one subject.
    """

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='exams'
    )

    title = models.CharField(max_length=200)

    # NEW FIELD
    target_class = models.CharField(
        max_length=10,
        choices=User.StudentClass.choices
    )

    duration_minutes = models.PositiveIntegerField(default=30)

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exams'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.target_class})"

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def total_marks(self):
        return sum(self.questions.values_list('marks', flat=True))


class Question(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    text = models.TextField()

    marks = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.text[:60]


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices'
    )

    text = models.CharField(max_length=500)

    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:60]