from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class User(AbstractUser):
    """
    Single user model for all three roles. A `role` field determines
    what a user can do; access control is enforced in views via the
    mixins/decorators in this app, not via Django permissions/groups,
    to keep things simple.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'

    class StudentClass(models.TextChoices):
        JSS1 = 'JSS1', 'JSS1'
        JSS2 = 'JSS2', 'JSS2'
        JSS3 = 'JSS3', 'JSS3'
        SSS1 = 'SSS1', 'SSS1'
        SSS2 = 'SSS2', 'SSS2'
        SSS3 = 'SSS3', 'SSS3'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    # Only relevant for students; harmless/unused for other roles.
    admission_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    student_class = models.CharField(
        max_length=10,
        choices=StudentClass.choices,
        blank=True,
        null=True,
        help_text="Only used for students"
    )

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT