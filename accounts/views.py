from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
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
    TeacherStudentCreationForm,
    TeacherStudentEditForm,
)
from .models import User


# ==========================
# Dashboard
# ==========================

@login_required
def dashboard_redirect(request):
    """
    Send users to the appropriate dashboard based on their role.
    """

    if request.user.role == User.Role.SUPER_ADMIN:
        return render(
            request,
            "accounts/dashboard_placeholder.html",
            {
                "role": request.user.role,
            },
        )

    if request.user.role == User.Role.TEACHER:
        return render(
            request,
            "accounts/dashboard_placeholder.html",
            {
                "role": request.user.role,
            },
        )

    if request.user.role == User.Role.STUDENT:
        return render(
            request,
            "accounts/dashboard_placeholder.html",
            {
                "role": request.user.role,
            },
        )

    return redirect("accounts:home")


# ==========================
# Super Admin
# ==========================

@role_required("SUPER_ADMIN")
def create_teacher(request):

    if request.method == "POST":

        form = TeacherCreationForm(request.POST)

        if form.is_valid():

            teacher = form.save()

            messages.success(
                request,
                f"Teacher account '{teacher.username}' created successfully.",
            )

            return redirect("accounts:user_list")

    else:
        form = TeacherCreationForm()

    return render(
        request,
        "accounts/create_teacher.html",
        {
            "form": form,
        },
    )


@role_required("SUPER_ADMIN")
def create_student(request):

    if request.method == "POST":

        form = StudentCreationForm(request.POST)

        if form.is_valid():

            student = form.save()

            messages.success(
                request,
                f"Student account '{student.username}' created successfully.",
            )

            return redirect("accounts:user_list")

    else:
        form = StudentCreationForm()

    return render(
        request,
        "accounts/create_student.html",
        {
            "form": form,
        },
    )


@role_required("SUPER_ADMIN")
def user_list(request):

    role_filter = request.GET.get("role", "")

    users = (
        User.objects
        .exclude(id=request.user.id)
        .order_by("role", "username")
    )

    if role_filter in {"TEACHER", "STUDENT"}:
        users = users.filter(role=role_filter)

    return render(
        request,
        "accounts/user_list.html",
        {
            "users": users,
            "role_filter": role_filter,
        },
    )


@role_required("SUPER_ADMIN")
def reset_password(request, user_id):

    target_user = get_object_or_404(
        User,
        id=user_id,
    )

    if request.method == "POST":

        form = AdminPasswordResetForm(request.POST)

        if form.is_valid():

            target_user.set_password(
                form.cleaned_data["new_password1"]
            )

            target_user.save()

            messages.success(
                request,
                f"Password for '{target_user.username}' has been reset.",
            )

            return redirect("accounts:user_list")

    else:
        form = AdminPasswordResetForm()

    return render(
        request,
        "accounts/reset_password.html",
        {
            "form": form,
            "target_user": target_user,
        },
    )


# ==========================
# Landing Page
# ==========================

def home(request):

    return render(
        request,
        "landing.html",
    )


# ==========================
# Student Login
# ==========================

def student_login(request):

    if request.user.is_authenticated:
        logout(request)

    if request.method == "POST":

        form = StudentLoginForm(request.POST)

        if form.is_valid():

            user = form.cleaned_data["user"]

            login(request, user)

            return redirect(
                "accounts:dashboard_redirect"
            )

    else:

        form = StudentLoginForm()

    return render(
        request,
        "accounts/student_login.html",
        {
            "form": form,
        },
    )


# ==========================
# Teacher Login
# ==========================

def teacher_login(request):

    if request.user.is_authenticated:
        logout(request)

    if request.method == "POST":

        form = TeacherLoginForm(request.POST)

        if form.is_valid():

            user = form.cleaned_data["user"]

            login(request, user)

            return redirect(
                "accounts:dashboard_redirect"
            )

    else:

        form = TeacherLoginForm()

    return render(
        request,
        "accounts/teacher_login.html",
        {
            "form": form,
        },
    )


# ==========================
# Student AJAX
# ==========================

@require_GET
def students_by_class(request):
    """
    Return active students in a selected class as JSON.
    """

    student_class = request.GET.get(
        "class",
        "",
    )

    students = (
        User.objects
        .filter(
            role=User.Role.STUDENT,
            student_class=student_class,
            is_active=True,
        )
        .order_by(
            "first_name",
            "last_name",
        )
    )

    data = [
        {
            "id": student.id,
            "name": f"{student.first_name} {student.last_name}".strip(),
            "admission_number": student.admission_number,
        }
        for student in students
    ]

    return JsonResponse(
        data,
        safe=False,
    )


# ==========================
# Teacher - Student Management
# ==========================

@role_required("TEACHER")
def teacher_students(request):
    """
    Display all students so a teacher can manage them.
    """

    students = (
        User.objects
        .filter(
            role=User.Role.STUDENT,
        )
        .order_by(
            "student_class",
            "first_name",
            "last_name",
        )
    )

    return render(
        request,
        "accounts/teacher_students.html",
        {
            "students": students,
        },
    )


@role_required("TEACHER")
def teacher_add_student(request):
    """
    Allow a teacher to create a new student account.
    """

    if request.method == "POST":

        form = TeacherStudentCreationForm(
            request.POST
        )

        if form.is_valid():

            student = form.save()

            messages.success(
                request,
                f"Student '{student.username}' added successfully.",
            )

            return redirect(
                "accounts:teacher_students"
            )

    else:

        form = TeacherStudentCreationForm()

    return render(
        request,
        "accounts/teacher_student_form.html",
        {
            "form": form,
            "editing": False,
        },
    )


@role_required("TEACHER")
def teacher_edit_student(request, user_id):
    """
    Allow a teacher to edit a student account.
    """

    student = get_object_or_404(
        User,
        id=user_id,
        role=User.Role.STUDENT,
    )

    if request.method == "POST":

        form = TeacherStudentEditForm(
            request.POST,
            instance=student,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                f"Student '{student.username}' updated successfully.",
            )

            return redirect(
                "accounts:teacher_students"
            )

    else:

        form = TeacherStudentEditForm(
            instance=student
        )

    return render(
        request,
        "accounts/teacher_student_form.html",
        {
            "form": form,
            "student": student,
            "editing": True,
        },
    )


@role_required("TEACHER")
def teacher_delete_student(request, user_id):
    """
    Allow a teacher to remove a student account.
    """

    student = get_object_or_404(
        User,
        id=user_id,
        role=User.Role.STUDENT,
    )

    if request.method == "POST":

        username = student.username

        student.delete()

        messages.success(
            request,
            f"Student '{username}' removed successfully.",
        )

        return redirect(
            "accounts:teacher_students"
        )

    return render(
        request,
        "accounts/teacher_student_confirm_delete.html",
        {
            "student": student,
        },
    )