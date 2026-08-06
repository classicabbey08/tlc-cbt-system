from django.utils import timezone

from .models import ExamAttempt, StudentAnswer


def finalize_attempt(attempt: ExamAttempt, submitted_choice_ids: dict):
    """
    Persists the student's answers, computes the score, and marks the
    attempt as submitted. `submitted_choice_ids` maps
    {question_id: choice_id_or_None}. Called both for a normal submit
    and for a server-detected timeout (in which case it's called with
    whatever answers were posted, or an empty dict).

    Server-validated: this is the single place attempts get scored,
    and it is only ever reached through view logic that has already
    confirmed the attempt belongs to the requesting student and is
    not already submitted — the client's countdown display has no
    bearing on whether points are awarded.
    """
    if attempt.status == ExamAttempt.Status.SUBMITTED:
        return attempt

    total_score = 0
    for question in attempt.exam.questions.prefetch_related('choices'):
        choice_id = submitted_choice_ids.get(question.id)
        selected_choice = None
        if choice_id:
            selected_choice = next(
                (c for c in question.choices.all() if c.id == int(choice_id)), None
            )

        StudentAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={'selected_choice': selected_choice},
        )

        if selected_choice and selected_choice.is_correct:
            total_score += question.marks

    attempt.score = total_score
    attempt.status = ExamAttempt.Status.SUBMITTED
    attempt.submitted_at = timezone.now()
    attempt.save()
    return attempt
