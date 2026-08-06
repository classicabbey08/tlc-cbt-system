from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .decorators import role_required
from .forms import (
    AdminPasswordResetForm,
    StudentCreationForm,
    TeacherCreationForm,
    StudentLoginForm,
    TeacherLoginForm,
)
from .models import User


@login_required
def dashboard_redirect(request):
    """
    Single entry point after login. Sends each role to its own
    dashboard. The actual dashboard pages are built in a later phase
    (core app) — for now this renders a simple placeholder so the
    login flow is fully testable end-to-end.
    """
    return render(request, 'accounts/dashboard_placeholder.html', {'role': request.user.role})


@role_required('SUPER_ADMIN')
def create_teacher(request):
    if request.method == 'POST':
        form = TeacherCreationForm(request.POST)
        if form.is_valid():
            teacher = form.save()
            messages.success(request, f"Teacher account '{teacher.username}' created successfully.")
            return redirect('accounts:user_list')
    else:
        form = TeacherCreationForm()
    return render(request, 'accounts/create_teacher.html', {'form': form})


@role_required('SUPER_ADMIN')
def create_student(request):
    if request.method == 'POST':
        form = StudentCreationForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"Student account '{student.username}' created successfully.")
            return redirect('accounts:user_list')
    else:
        form = StudentCreationForm()
    return render(request, 'accounts/create_student.html', {'form': form})


@role_required('SUPER_ADMIN')
def user_list(request):
    role_filter = request.GET.get('role', '')
    users = User.objects.exclude(id=request.user.id).order_by('role', 'username')
    if role_filter in {'TEACHER', 'STUDENT'}:
        users = users.filter(role=role_filter)
    return render(request, 'accounts/user_list.html', {'users': users, 'role_filter': role_filter})


@role_required('SUPER_ADMIN')
def reset_password(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            target_user.set_password(form.cleaned_data['new_password1'])
            target_user.save()
            messages.success(request, f"Password for '{target_user.username}' has been reset.")
            return redirect('accounts:user_list')
    else:
        form = AdminPasswordResetForm()
    return render(request, 'accounts/reset_password.html', {'form': form, 'target_user': target_user})


# ==========================
# Landing Page
# ==========================
def home(request):
    return render(request, "landing.html")


# ==========================
# Custom Login Views
# ==========================

def student_login(request):
    # If someone is already logged in, log them out first
    if request.user.is_authenticated:
        logout(request)

    if request.method == "POST":
        form = StudentLoginForm(request.POST)

        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            return redirect("accounts:dashboard_redirect")

    else:
        form = StudentLoginForm()

    return render(
        request,
        "accounts/student_login.html",
        {"form": form},
    )


def teacher_login(request):
    # If someone is already logged in, log them out first
    if request.user.is_authenticated:
        logout(request)

    if request.method == "POST":
        form = TeacherLoginForm(request.POST)

        if form.is_valid():
            user = form.cleaned_data["user"]
            login(request, user)
            return redirect("accounts:dashboard_redirect")

    else:
        form = TeacherLoginForm()

    return render(
        request,
        "accounts/teacher_login.html",
        {"form": form},
    )
@require_GET
def students_by_class(request):
    """Return students in a class as JSON."""
    student_class = request.GET.get("class", "")

    students = User.objects.filter(
        role=User.Role.STUDENT,
        student_class=student_class,
    ).order_by("first_name", "last_name")

    data = [
        {
            "id": s.id,
            "name": f"{s.first_name} {s.last_name}".strip(),
            "admission_number": s.admission_number,
        }
        for s in students
    ]

    return JsonResponse(data, safe=False)