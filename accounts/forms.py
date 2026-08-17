from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm

from .models import User


class TeacherCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER

        if commit:
            user.save()

        return user


class StudentCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "admission_number",
            "student_class",
            "department",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "admission_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "student_class": forms.Select(
                attrs={"class": "form-select"}
            ),
            "department": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT

        if user.student_class in [
            User.StudentClass.JSS1,
            User.StudentClass.JSS2,
            User.StudentClass.JSS3,
        ]:
            user.department = User.Department.GENERAL

        if commit:
            user.save()

        return user


class TeacherStudentCreationForm(UserCreationForm):
    """
    Form used by teachers to create student accounts.
    """

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "admission_number",
            "student_class",
            "department",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "admission_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "student_class": forms.Select(
                attrs={"class": "form-select"}
            ),
            "department": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def save(self, commit=True):
        user = super().save(commit=False)

        user.role = User.Role.STUDENT

        # JSS students are always General
        if user.student_class in [
            User.StudentClass.JSS1,
            User.StudentClass.JSS2,
            User.StudentClass.JSS3,
        ]:
            user.department = User.Department.GENERAL

        if commit:
            user.save()

        return user


class TeacherStudentEditForm(forms.ModelForm):
    """
    Form used by teachers to edit student accounts.
    """

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "admission_number",
            "student_class",
            "department",
            "is_active",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "admission_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "student_class": forms.Select(
                attrs={"class": "form-select"}
            ),
            "department": forms.Select(
                attrs={"class": "form-select"}
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def clean_department(self):
        department = self.cleaned_data.get("department")
        student_class = self.cleaned_data.get("student_class")

        if student_class in [
            User.StudentClass.JSS1,
            User.StudentClass.JSS2,
            User.StudentClass.JSS3,
        ]:
            return User.Department.GENERAL

        return department


class AdminPasswordResetForm(forms.Form):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput,
    )

    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput,
    )

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("new_password1") != cleaned.get("new_password2"):
            raise forms.ValidationError(
                "The two password fields didn't match."
            )

        return cleaned


class StudentLoginForm(forms.Form):
    student_class = forms.ChoiceField(
        label="Class",
        choices=[("", "---------")] + list(User.StudentClass.choices),
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_student_class",
            }
        ),
    )

    student = forms.ModelChoiceField(
        label="Student Name",
        queryset=User.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "id": "id_student",
            }
        ),
    )

    pin = forms.CharField(
        label="PIN",
        max_length=10,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your PIN",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "student_class" in self.data:
            student_class = self.data.get("student_class")

            self.fields["student"].queryset = (
                User.objects.filter(
                    role=User.Role.STUDENT,
                    student_class=student_class,
                    is_active=True,
                )
                .order_by("first_name", "last_name")
            )

    def clean(self):
        cleaned = super().clean()

        student = cleaned.get("student")
        pin = cleaned.get("pin")

        if student and pin:
            user = authenticate(
                username=student.username,
                password=pin,
            )

            if user is None:
                raise forms.ValidationError(
                    "Incorrect PIN."
                )

            if not user.is_student:
                raise forms.ValidationError(
                    "This account is not a student account."
                )

            if not user.is_active:
                raise forms.ValidationError(
                    "This student account is inactive."
                )

            cleaned["user"] = user

        return cleaned


class TeacherLoginForm(forms.Form):
    teacher = forms.ModelChoiceField(
        label="Teacher Name",
        queryset=User.objects.filter(
            role=User.Role.TEACHER,
            is_active=True,
        ).order_by(
            "first_name",
            "last_name",
            "username",
        ),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    pin = forms.CharField(
        label="PIN",
        max_length=10,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your PIN",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()

        teacher = cleaned.get("teacher")
        pin = cleaned.get("pin")

        if teacher and pin:
            user = authenticate(
                username=teacher.username,
                password=pin,
            )

            if user is None:
                raise forms.ValidationError(
                    "Incorrect PIN."
                )

            if not user.is_teacher:
                raise forms.ValidationError(
                    "This account is not a teacher account."
                )

            if not user.is_active:
                raise forms.ValidationError(
                    "This teacher account is inactive."
                )

            cleaned["user"] = user

        return cleaned