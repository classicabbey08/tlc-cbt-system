from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from exams.models import Exam

from .models import ExamAttempt
from .utils import finalize_attempt


# ---------- Student ----------

@role_required("STUDENT")
def available_exams(request):
    """
    Show only exams that belong to the student's class.
    For SSS students, also filter by department.
    """

    if request.user.student_class.startswith("JSS"):
        exams = Exam.objects.filter(
            is_active=True,
            target_class=request.user.student_class,
        ).select_related("subject")
    else:
        exams = Exam.objects.filter(
            is_active=True,
            target_class=request.user.student_class,
            department=request.user.department,
        ).select_related("subject")

    my_attempts = {
        attempt.exam_id: attempt
        for attempt in ExamAttempt.objects.filter(student=request.user)
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
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_active=True,
    )

    attempt, created = ExamAttempt.objects.get_or_create(
        student=request.user,
        exam=exam,
    )

    if attempt.status == ExamAttempt.Status.SUBMITTED:
        return redirect("attempts:result_detail", attempt_id=attempt.id)

    return redirect("attempts:take_exam", attempt_id=attempt.id)


@role_required("STUDENT")
def take_exam(request, attempt_id):
    attempt = get_object_or_404(
        ExamAttempt,
        id=attempt_id,
        student=request.user,
    )

    if attempt.status == ExamAttempt.Status.SUBMITTED:
        return redirect("attempts:result_detail", attempt_id=attempt.id)

    # Auto-submit if time has expired
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

    questions = attempt.exam.questions.prefetch_related("choices")

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
        choice_id = request.POST.get(f"question_{question.id}")

        if choice_id:
            submitted_choice_ids[question.id] = choice_id

    finalize_attempt(
        attempt,
        submitted_choice_ids,
    )

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
    Students only see confirmation.
    They never see scores or answers.
    """

    attempt = get_object_or_404(
        ExamAttempt,
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


# ---------- Teacher ----------

@role_required("TEACHER")
def teacher_results(request):
    """
    Teachers see results only for exams they created.
    """

    attempts = (
        ExamAttempt.objects.filter(
            exam__created_by=request.user,
            status=ExamAttempt.Status.SUBMITTED,
        )
        .select_related("student", "exam")
        .order_by("-submitted_at")
    )

    return render(
        request,
        "attempts/teacher_results.html",
        {
            "attempts": attempts,
        },
    )


# ---------- Super Admin ----------

@role_required("SUPER_ADMIN")
def admin_results(request):
    """
    Super Admin sees every submitted exam result.
    """

    attempts = (
        ExamAttempt.objects.filter(
            status=ExamAttempt.Status.SUBMITTED,
        )
        .select_related(
            "student",
            "exam",
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