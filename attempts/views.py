from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import User
from exams.models import Exam

from .models import ExamAttempt
from .utils import finalize_attempt


# =========================================================
# Helpers
# =========================================================

def student_can_take_exam(user, exam):
    """
    Check whether a student belongs to the class/department
    targeted by the exam.
    """

    if exam.target_class != user.student_class:
        return False

    # JSS students are always General.
    if user.student_class.startswith("JSS"):
        return exam.department == User.Department.GENERAL

    # SSS students must match the exam department.
    return exam.department == user.department


# =========================================================
# Student
# =========================================================

@role_required("STUDENT")
def available_exams(request):
    """
    Show only active exams available to the logged-in student.
    """

    exams = Exam.objects.filter(
        is_active=True,
        target_class=request.user.student_class,
    ).select_related(
        "subject",
        "created_by",
    )

    if request.user.student_class.startswith("JSS"):
        exams = exams.filter(
            department=User.Department.GENERAL
        )
    else:
        exams = exams.filter(
            department=request.user.department
        )

    exams = exams.order_by("-created_at")

    my_attempts = {
        attempt.exam_id: attempt
        for attempt in ExamAttempt.objects.filter(
            student=request.user
        )
    }

    exam_rows = []

    for exam in exams:
        exam_rows.append(
            {
                "exam": exam,
                "attempt": my_attempts.get(exam.id),
            }
        )

    return render(
        request,
        "attempts/available_exams.html",
        {
            "exam_rows": exam_rows,
        },
    )


@role_required("STUDENT")
def start_exam(request, exam_id):
    """
    Start an exam only if the student is eligible for it.
    """

    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_active=True,
    )

    if not student_can_take_exam(request.user, exam):
        messages.error(
            request,
            "You are not eligible to take this exam.",
        )

        return redirect(
            "attempts:available_exams"
        )

    attempt, created = ExamAttempt.objects.get_or_create(
        student=request.user,
        exam=exam,
    )

    # Already submitted → show confirmation/result page.
    if attempt.status == ExamAttempt.Status.SUBMITTED:
        return redirect(
            "attempts:result_detail",
            attempt_id=attempt.id,
        )

    # Existing unfinished attempt → continue it.
    return redirect(
        "attempts:take_exam",
        attempt_id=attempt.id,
    )


@role_required("STUDENT")
def take_exam(request, attempt_id):
    """
    Display an active exam attempt.
    """

    attempt = get_object_or_404(
        ExamAttempt.objects.select_related(
            "exam",
            "exam__subject",
        ),
        id=attempt_id,
        student=request.user,
    )

    if attempt.status == ExamAttempt.Status.SUBMITTED:
        return redirect(
            "attempts:result_detail",
            attempt_id=attempt.id,
        )

    # Server-side timeout check.
    if attempt.is_expired:
        finalize_attempt(
            attempt,
            submitted_choice_ids={},
        )

        messages.warning(
            request,
            "Time is up. Your exam has been submitted automatically.",
        )

        return redirect(
            "attempts:result_detail",
            attempt_id=attempt.id,
        )

    questions = (
        attempt.exam.questions
        .prefetch_related("choices")
        .all()
    )

    return render(
        request,
        "attempts/take_exam.html",
        {
            "attempt": attempt,
            "exam": attempt.exam,
            "questions": questions,
            "seconds_remaining": attempt.seconds_remaining,
        },
    )


@role_required("STUDENT")
def submit_exam(request, attempt_id):
    """
    Submit and score an exam attempt.
    """

    attempt = get_object_or_404(
        ExamAttempt,
        id=attempt_id,
        student=request.user,
    )

    if request.method != "POST":
        return redirect(
            "attempts:take_exam",
            attempt_id=attempt.id,
        )

    if attempt.status == ExamAttempt.Status.SUBMITTED:
        return redirect(
            "attempts:result_detail",
            attempt_id=attempt.id,
        )

    submitted_choice_ids = {}

    for question in attempt.exam.questions.all():
        choice_id = request.POST.get(
            f"question_{question.id}"
        )

        if choice_id:
            submitted_choice_ids[question.id] = choice_id

    # The server is the final authority on the timer.
    if attempt.is_expired:
        messages.warning(
            request,
            "The exam time has expired. Your exam has been submitted.",
        )

    finalize_attempt(
        attempt,
        submitted_choice_ids,
    )

    if not attempt.is_expired:
        messages.success(
            request,
            "Exam submitted successfully.",
        )

    return redirect(
        "attempts:result_detail",
        attempt_id=attempt.id,
    )


@role_required("STUDENT")
def result_detail(request, attempt_id):
    """
    Students only see submission confirmation.
    They do not see scores or correct answers.
    """

    attempt = get_object_or_404(
        ExamAttempt.objects.select_related(
            "exam",
            "exam__subject",
        ),
        id=attempt_id,
        student=request.user,
    )

    if attempt.status != ExamAttempt.Status.SUBMITTED:
        return redirect(
            "attempts:take_exam",
            attempt_id=attempt.id,
        )

    return render(
        request,
        "attempts/result_detail.html",
        {
            "attempt": attempt,
        },
    )


# =========================================================
# Teacher Results
# =========================================================

@role_required("TEACHER")
def teacher_results(request):
    """
    Teachers can only see submitted attempts belonging
    to exams they created.
    """

    attempts = (
        ExamAttempt.objects.filter(
            exam__created_by=request.user,
            status=ExamAttempt.Status.SUBMITTED,
        )
        .select_related(
            "student",
            "exam",
            "exam__subject",
        )
        .order_by("-submitted_at")
    )

    return render(
        request,
        "attempts/teacher_results.html",
        {
            "attempts": attempts,
        },
    )


@role_required("TEACHER")
def teacher_result_detail(request, attempt_id):
    """
    Teacher views the full result of a student who took
    one of the teacher's exams.
    """

    attempt = get_object_or_404(
        ExamAttempt.objects.select_related(
            "student",
            "exam",
            "exam__subject",
        ),
        id=attempt_id,
        exam__created_by=request.user,
        status=ExamAttempt.Status.SUBMITTED,
    )

    answers = (
        attempt.answers
        .select_related(
            "question",
            "selected_choice",
        )
        .prefetch_related(
            "question__choices",
        )
        .order_by("question_id")
    )

    return render(
        request,
        "attempts/teacher_result_detail.html",
        {
            "attempt": attempt,
            "answers": answers,
        },
    )


# =========================================================
# Super Admin Results
# =========================================================

@role_required("SUPER_ADMIN")
def admin_results(request):
    """
    Super Admin sees every submitted exam attempt.
    """

    attempts = (
        ExamAttempt.objects.filter(
            status=ExamAttempt.Status.SUBMITTED,
        )
        .select_related(
            "student",
            "exam",
            "exam__subject",
            "exam__created_by",
        )
        .order_by("-submitted_at")
    )

    return render(
        request,
        "attempts/admin_results.html",
        {
            "attempts": attempts,
        },
    )


@role_required("SUPER_ADMIN")
def admin_result_detail(request, attempt_id):
    """
    Super Admin can inspect any submitted result.
    """

    attempt = get_object_or_404(
        ExamAttempt.objects.select_related(
            "student",
            "exam",
            "exam__subject",
            "exam__created_by",
        ),
        id=attempt_id,
        status=ExamAttempt.Status.SUBMITTED,
    )

    answers = (
        attempt.answers
        .select_related(
            "question",
            "selected_choice",
        )
        .prefetch_related(
            "question__choices",
        )
        .order_by("question_id")
    )

    return render(
        request,
        "attempts/admin_result_detail.html",
        {
            "attempt": attempt,
            "answers": answers,
        },
    )