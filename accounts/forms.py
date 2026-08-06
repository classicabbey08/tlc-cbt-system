from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate

from .models import User


class TeacherCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER
        if commit:
            user.save()
        return user


class StudentCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'admission_number', 'student_class']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        if commit:
            user.save()
        return user


class AdminPasswordResetForm(forms.Form):
    """
    Lets a Super Admin set a new password for any user without
    needing to know the old one.
    """
    new_password1 = forms.CharField(label='New password', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='Confirm new password', widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("The two password fields didn't match.")
        return cleaned_data


class StudentLoginForm(forms.Form):
    student_class = forms.ChoiceField(
        label="Class",
        choices=[('', '---------')] + list(User.StudentClass.choices),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_student_class'})
    )
    student = forms.ModelChoiceField(
        label="Student Name",
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_student'})
    )
    pin = forms.CharField(
        label="PIN",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your PIN',
            'maxlength': '10'
        }),
        max_length=10
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'student_class' in self.data:
            try:
                sc = self.data.get('student_class')
                self.fields['student'].queryset = User.objects.filter(
                    role=User.Role.STUDENT,
                    student_class=sc
                ).order_by('first_name', 'last_name')
            except (ValueError, TypeError):
                self.fields['student'].queryset = User.objects.none()
        else:
            self.fields['student'].queryset = User.objects.none()

    def clean(self):
        cleaned = super().clean()
        student = cleaned.get('student')
        pin = cleaned.get('pin')
        if student and pin:
            user = authenticate(username=student.username, password=pin)
            if user is None:
                raise forms.ValidationError("Incorrect PIN. Please try again.")
            if not user.is_student:
                raise forms.ValidationError("This account is not a student account.")
            cleaned['user'] = user
        return cleaned


class TeacherLoginForm(forms.Form):
    teacher = forms.ModelChoiceField(
        label="Teacher Name",
        queryset=User.objects.filter(role=User.Role.TEACHER).order_by('first_name', 'last_name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    pin = forms.CharField(
        label="PIN",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your PIN'
        }),
        max_length=10
    )

    def clean(self):
        cleaned = super().clean()
        teacher = cleaned.get('teacher')
        pin = cleaned.get('pin')
        if teacher and pin:
            user = authenticate(username=teacher.username, password=pin)
            if user is None:
                raise forms.ValidationError("Incorrect PIN. Please try again.")
            if not user.is_teacher:
                raise forms.ValidationError("This account is not a teacher account.")
            cleaned['user'] = user
        return cleaned