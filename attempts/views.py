from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import User
from exams.models import Exam

from .models import ExamAttempt
from .utils import finalize_attempt


# =========================================================
# HELPERS
# =========================================================

def student_can_take_exam(user, exam):
    """
    Check whether a student belongs to the class/department
    targeted by the exam.

    Department applies ONLY to SS students.

    JSS students:
        - Must match the target class.
        - Must have/use GENERAL department.

    SS students:
        - Must match the target class.
        - Must match the exam department.
    """

    # -----------------------------------------------------
    # CLASS MUST ALWAYS MATCH
    # -----------------------------------------------------

    if exam.target_class != user.student_class:
        return False

    # -----------------------------------------------------
    # DEPARTMENT ONLY APPLIES TO SS STUDENTS
    # -----------------------------------------------------

    if user.student_class.startswith("JSS"):

        return (
            exam.department
            == User.Department.GENERAL
        )

    # -----------------------------------------------------
    # SS STUDENTS
    # -----------------------------------------------------

    return (
        exam.department
        == user.department
    )


# =========================================================
# STUDENT - AVAILABLE EXAMS
# =========================================================

@role_required("STUDENT")
def available_exams(request):
    """
    Show only active exams available to the logged-in student.

    Rules:

    JSS:
        Class must match.
        Department must be GENERAL.

    SS:
        Class must match.
        Department must match the student's department.
    """

    user = request.user

    # -----------------------------------------------------
    # START WITH ACTIVE EXAMS FOR THE STUDENT'S CLASS
    # -----------------------------------------------------

    exams = (
        Exam.objects
        .filter(
            is_active=True,
            target_class=user.student_class,
        )
        .select_related(
            "subject",
            "created_by",
        )
    )

    # -----------------------------------------------------
    # JSS STUDENTS
    # -----------------------------------------------------

    if user.student_class.startswith("JSS"):

        exams = exams.filter(
            department=User.Department.GENERAL
        )

    # -----------------------------------------------------
    # SS STUDENTS
    # -----------------------------------------------------

    else:

        exams = exams.filter(
            department=user.department
        )

    # -----------------------------------------------------
    # NEWEST EXAMS FIRST
    # -----------------------------------------------------

    exams = exams.order_by(
        "-created_at"
    )

    # -----------------------------------------------------
    # FIND THIS STUDENT'S EXISTING ATTEMPTS
    # -----------------------------------------------------

    my_attempts = {
        attempt.exam_id: attempt
        for attempt in ExamAttempt.objects.filter(
            student=user
        )
    }

    # -----------------------------------------------------
    # BUILD EXAM ROWS
    # -----------------------------------------------------

    exam_rows = []

    for exam in exams:

        exam_rows.append(
            {
                "exam": exam,
                "attempt": my_attempts.get(
                    exam.id
                ),
            }
        )

    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------

    return render(
        request,
        "attempts/available_exams.html",
        {
            "exam_rows": exam_rows,
        },
    )


# =========================================================
# STUDENT - START EXAM
# =========================================================

@role_required("STUDENT")
def start_exam(request, exam_id):
    """
    Start an exam only if the student is eligible.

    The server checks both:
        1. Class
        2. Department for SS students
    """

    exam = get_object_or_404(
        Exam,
        id=exam_id,
        is_active=True,
    )

    # -----------------------------------------------------
    # CHECK ELIGIBILITY
    # -----------------------------------------------------

    if not student_can_take_exam(
        request.user,
        exam,
    ):

        messages.error(
            request,
            "You are not eligible to take this exam.",
        )

        return redirect(
            "attempts:available_exams"
        )

    # -----------------------------------------------------
    # GET OR CREATE ATTEMPT
    # -----------------------------------------------------

    attempt, created = (
        ExamAttempt.objects.get_or_create(
            student=request.user,
            exam=exam,
        )
    )

    # -----------------------------------------------------
    # ALREADY SUBMITTED
    # -----------------------------------------------------

    if (
        attempt.status
        == ExamAttempt.Status.SUBMITTED
    ):

        return redirect(
            "attempts:result_detail",
            attempt_id=attempt.id,
        )

    # -----------------------------------------------------
    # EXISTING UNFINISHED ATTEMPT
    # -----------------------------------------------------

    return redirect(
        "attempts:take_exam",
        attempt_id=attempt.id,
    )


# =========================================================
# STUDENT - TAKE EXAM
# =========================================================

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

    # -----------------------------------------------------
    # ALREADY SUBMITTED
    # -----------------------------------------------------

    if (
        attempt.status
        == ExamAttempt.Status.SUBMITTED
    ):

        return redirect(
            "attempts:result_detail",
            attempt_id=attempt.id,
        )

    # -----------------------------------------------------
    # SERVER-SIDE TIMEOUT CHECK
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # LOAD QUESTIONS
    # -----------------------------------------------------

    questions = (
        attempt.exam.questions
        .prefetch_related(
            "choices"
        )
        .all()
    )

    # -----------------------------------------------------
    # RENDER EXAM
    # -----------------------------------------------------

    return render(
        request,
        "attempts/take_exam.html",
        {
            "attempt": attempt,
            "exam": attempt.exam,
            "questions": questions,
            "seconds_remaining":
                attempt.seconds_remaining,
        },
    )


# =========================================================
# STUDENT - SUBMIT EXAM
# =========================================================

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

    # -----------------------------------------------------
    # ONLY POST IS ALLOWED FOR SUBMISSION
    # -----------------------------------------------------

    if request.method != "POST":

        return redirect(
            "attempts:take_exam",
            attempt_id=attempt.id,
        )

    # -----------------------------------------------------
    # ALREADY SUBMITTED
    # -----------------------------------------------------

    if (
        attempt.status
        == ExamAttempt.Status.SUBMITTED
    ):

        return redirect(
            "attempts:result_detail",
            attempt_id=attempt.id,
        )

    # -----------------------------------------------------
    # COLLECT ANSWERS
    # -----------------------------------------------------

    submitted_choice_ids = {}

    for question in attempt.exam.questions.all():

        choice_id = request.POST.get(
            f"question_{question.id}"
        )

        if choice_id:

            submitted_choice_ids[
                question.id
            ] = choice_id

    # -----------------------------------------------------
    # SERVER IS FINAL AUTHORITY ON TIMER
    # -----------------------------------------------------

    if attempt.is_expired:

        messages.warning(
            request,
            "The exam time has expired. Your exam has been submitted.",
        )

    # -----------------------------------------------------
    # FINALIZE ATTEMPT
    # -----------------------------------------------------

    finalize_attempt(
        attempt,
        submitted_choice_ids,
    )

    # -----------------------------------------------------
    # NORMAL SUBMISSION MESSAGE
    # -----------------------------------------------------

    if not attempt.is_expired:

        messages.success(
            request,
            "Exam submitted successfully.",
        )

    # -----------------------------------------------------
    # SHOW CONFIRMATION
    # -----------------------------------------------------

    return redirect(
        "attempts:result_detail",
        attempt_id=attempt.id,
    )


# =========================================================
# STUDENT - RESULT DETAIL
# =========================================================

@role_required("STUDENT")
def result_detail(request, attempt_id):
    """
    Students only see submission confirmation.

    Scores and correct answers are not shown here.
    """

    attempt = get_object_or_404(
        ExamAttempt.objects.select_related(
            "exam",
            "exam__subject",
        ),
        id=attempt_id,
        student=request.user,
    )

    # -----------------------------------------------------
    # NOT SUBMITTED YET
    # -----------------------------------------------------

    if (
        attempt.status
        != ExamAttempt.Status.SUBMITTED
    ):

        return redirect(
            "attempts:take_exam",
            attempt_id=attempt.id,
        )

    # -----------------------------------------------------
    # SHOW RESULT CONFIRMATION
    # -----------------------------------------------------

    return render(
        request,
        "attempts/result_detail.html",
        {
            "attempt": attempt,
        },
    )


# =========================================================
# TEACHER - RESULTS
# =========================================================

@role_required("TEACHER")
def teacher_results(request):
    """
    Teachers can only see submitted attempts belonging
    to exams they created.
    """

    attempts = (
        ExamAttempt.objects
        .filter(
            exam__created_by=request.user,
            status=ExamAttempt.Status.SUBMITTED,
        )
        .select_related(
            "student",
            "exam",
            "exam__subject",
        )
        .order_by(
            "-submitted_at"
        )
    )

    return render(
        request,
        "attempts/teacher_results.html",
        {
            "attempts": attempts,
        },
    )


# =========================================================
# TEACHER - RESULT DETAIL
# =========================================================

@role_required("TEACHER")
def teacher_result_detail(
    request,
    attempt_id,
):
    """
    Teacher views the full result of a student
    who took one of the teacher's exams.
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
        .order_by(
            "question_id"
        )
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
# SUPER ADMIN - RESULTS
# =========================================================

@role_required("SUPER_ADMIN")
def admin_results(request):
    """
    Super Admin sees every submitted exam attempt.
    """

    attempts = (
        ExamAttempt.objects
        .filter(
            status=ExamAttempt.Status.SUBMITTED,
        )
        .select_related(
            "student",
            "exam",
            "exam__subject",
            "exam__created_by",
        )
        .order_by(
            "-submitted_at"
        )
    )

    return render(
        request,
        "attempts/admin_results.html",
        {
            "attempts": attempts,
        },
    )


# =========================================================
# SUPER ADMIN - RESULT DETAIL
# =========================================================

@role_required("SUPER_ADMIN")
def admin_result_detail(
    request,
    attempt_id,
):
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
        .order_by(
            "question_id"
        )
    )

    return render(
        request,
        "attempts/admin_result_detail.html",
        {
            "attempt": attempt,
            "answers": answers,
        },
    )