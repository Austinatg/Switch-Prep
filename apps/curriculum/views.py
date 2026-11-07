
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
import random

from apps.notes.models import DailyNote
from .models import (
    Specialization, Module, Section, Topic, TopicProgress,
    TopicBookmark, Assessment, AssessmentAttempt,
    Quiz, QuizQuestion, QuizAttempt, UserQuestionMistake,
)


# ============================================================
# EXISTING CURRICULUM VIEWS
# ============================================================

@login_required
def specialization_list(request):
    specializations = Specialization.objects.filter(
        is_published=True
    ).annotate(
        modules_count=Count(
            "modules",
            filter=Q(modules__is_published=True),
            distinct=True
        ),
        topics_count=Count(
            "modules__sections__topics",
            filter=Q(
                modules__is_published=True,
                modules__sections__is_published=True,
                modules__sections__topics__is_published=True
            ),
            distinct=True
        )
    )

    query = request.GET.get("q", "").strip()

    if query:
        specializations = specializations.filter(
            Q(name__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
        )

    return render(request, "curriculum/specialization_list.html", {
        "specializations": specializations,
        "query": query,
        "active_page": "learning",
    })


@login_required
def specialization_detail(request, slug):
    specialization = get_object_or_404(
        Specialization,
        slug=slug,
        is_published=True
    )

    modules = specialization.modules.filter(
        is_published=True
    ).prefetch_related(
        "sections__topics",
        "quizzes"
    )

    topics = Topic.objects.filter(
        section__module__specialization=specialization,
        section__module__is_published=True,
        section__is_published=True,
        is_published=True
    )

    completed_ids = set(
        TopicProgress.objects.filter(
            user=request.user,
            topic__in=topics,
            is_completed=True
        ).values_list("topic_id", flat=True)
    )

    total = topics.count()
    completed = len(completed_ids)

    course_quizzes = Quiz.objects.filter(
        specialization=specialization,
        exam_type__in=[
            Quiz.ExamType.COURSE_ONE,
            Quiz.ExamType.COURSE_TWO,
        ],
        is_published=True
    )

    mistake_count = UserQuestionMistake.objects.filter(
        user=request.user,
        specialization=specialization,
        is_resolved=False
    ).count()

    return render(request, "curriculum/specialization_detail.html", {
        "specialization": specialization,
        "modules": modules,
        "completed_ids": completed_ids,
        "total_topics": total,
        "completed_topics": completed,
        "progress_percent": round(completed * 100 / total) if total else 0,
        "course_quizzes": course_quizzes,
        "mistake_count": mistake_count,
        "active_page": "learning",
    })


@login_required
def topic_detail(request, specialization_slug, topic_slug):
    topic = get_object_or_404(
        Topic.objects.select_related(
            "section__module__specialization"
        ).prefetch_related(
            "resources",
            "code_examples",
            "prerequisites"
        ),
        slug=topic_slug,
        is_published=True,
        section__is_published=True,
        section__module__is_published=True,
        section__module__specialization__slug=specialization_slug,
        section__module__specialization__is_published=True,
    )

    progress, _ = TopicProgress.objects.get_or_create(
        user=request.user,
        topic=topic
    )

    progress.last_opened_at = timezone.now()
    progress.save(update_fields=["last_opened_at", "updated_at"])

    all_topics = list(
        Topic.objects.filter(
            section__module__specialization=topic.section.module.specialization,
            section__module__is_published=True,
            section__is_published=True,
            is_published=True
        ).select_related(
            "section__module"
        ).order_by(
            "section__module__display_order",
            "section__display_order",
            "display_order",
            "id"
        )
    )

    current_index = next(
        (i for i, item in enumerate(all_topics) if item.pk == topic.pk),
        0
    )

    previous_topic = (
        all_topics[current_index - 1]
        if current_index > 0 else None
    )

    next_topic = (
        all_topics[current_index + 1]
        if current_index + 1 < len(all_topics) else None
    )

    prerequisites = topic.prerequisites.filter(is_published=True)

    completed_prereq = set(
        TopicProgress.objects.filter(
            user=request.user,
            topic__in=prerequisites,
            is_completed=True
        ).values_list("topic_id", flat=True)
    )

    blocked = [
        item for item in prerequisites
        if item.pk not in completed_prereq
    ]

    bookmarked = TopicBookmark.objects.filter(
        user=request.user,
        topic=topic
    ).exists()

    section_assessments = Assessment.objects.filter(
        section=topic.section,
        is_published=True
    ).prefetch_related("questions")

    lesson_quiz = Quiz.objects.filter(
        topic=topic,
        exam_type=Quiz.ExamType.LESSON,
        is_published=True
    ).first()

    lesson_quiz_attempt = None

    if lesson_quiz:
        lesson_quiz_attempt = QuizAttempt.objects.filter(
            user=request.user,
            quiz=lesson_quiz
        ).first()

    daily_note = DailyNote.objects.filter(
        user=request.user,
        learning_date=timezone.localdate(),
        title=""
    ).first()
    note_points = daily_note.points.all() if daily_note else []

    return render(request, "curriculum/topic_detail.html", {
        "topic": topic,
        "progress": progress,
        "blocked_prerequisites": blocked,
        "active_page": "learning",
        "specialization": topic.section.module.specialization,
        "previous_topic": previous_topic,
        "next_topic": next_topic,
        "bookmarked": bookmarked,
        "section_assessments": section_assessments,
        "topic_position": current_index + 1,
        "topic_total": len(all_topics),
        "lesson_quiz": lesson_quiz,
        "lesson_quiz_attempt": lesson_quiz_attempt,
        "note_points": note_points,
    })


@login_required
@require_POST
def toggle_topic_completion(request, topic_id):
    topic = get_object_or_404(
        Topic,
        pk=topic_id,
        is_published=True
    )

    progress, _ = TopicProgress.objects.get_or_create(
        user=request.user,
        topic=topic
    )

    if progress.is_completed:
        progress.is_completed = False
        messages.info(request, "Topic marked as in progress.")

    else:
        lesson_quiz = Quiz.objects.filter(
            topic=topic,
            exam_type=Quiz.ExamType.LESSON,
            is_published=True
        ).first()

        if lesson_quiz and not QuizAttempt.objects.filter(
            user=request.user,
            quiz=lesson_quiz
        ).exists():
            messages.error(
                request,
                "Complete this lesson's MCQ examination before marking the lesson complete."
            )
            return redirect(
                "curriculum:topic_detail",
                specialization_slug=topic.section.module.specialization.slug,
                topic_slug=topic.slug
            )

        unmet = topic.prerequisites.filter(
            is_published=True
        ).exclude(
            user_progress__user=request.user,
            user_progress__is_completed=True
        )

        if unmet.exists():
            messages.error(
                request,
                "Complete the topic prerequisites before marking this topic complete."
            )
            return redirect(
                "curriculum:topic_detail",
                specialization_slug=topic.section.module.specialization.slug,
                topic_slug=topic.slug
            )

        progress.is_completed = True
        messages.success(request, "Great work! Topic marked as completed.")

    progress.save()

    return redirect(
        "curriculum:topic_detail",
        specialization_slug=topic.section.module.specialization.slug,
        topic_slug=topic.slug
    )


@login_required
@require_POST
def toggle_bookmark(request, topic_id):
    topic = get_object_or_404(
        Topic,
        pk=topic_id,
        is_published=True
    )

    bookmark, created = TopicBookmark.objects.get_or_create(
        user=request.user,
        topic=topic
    )

    if not created:
        bookmark.delete()
        messages.info(request, "Bookmark removed.")
    else:
        messages.success(request, "Topic bookmarked.")

    return redirect(
        "curriculum:topic_detail",
        specialization_slug=topic.section.module.specialization.slug,
        topic_slug=topic.slug
    )


# ============================================================
# EXISTING SECTION ASSESSMENT VIEWS
# ============================================================

@login_required
def assessment_detail(request, assessment_id):
    assessment = get_object_or_404(
        Assessment.objects.prefetch_related("questions__choices"),
        pk=assessment_id,
        is_published=True,
        section__is_published=True,
        section__module__is_published=True,
        section__module__specialization__is_published=True,
    )

    previous_attempts = AssessmentAttempt.objects.filter(
        user=request.user,
        assessment=assessment
    )

    return render(request, "curriculum/assessment_detail.html", {
        "assessment": assessment,
        "previous_attempts": previous_attempts,
        "active_page": "learning",
    })


@login_required
@require_POST
def submit_assessment(request, assessment_id):
    assessment = get_object_or_404(
        Assessment.objects.prefetch_related("questions__choices"),
        pk=assessment_id,
        is_published=True,
        section__is_published=True,
        section__module__is_published=True,
        section__module__specialization__is_published=True,
    )

    questions = list(assessment.questions.all())

    if not questions:
        messages.error(
            request,
            "This assessment does not have any questions yet."
        )
        return redirect(
            "curriculum:assessment_detail",
            assessment_id=assessment.id
        )

    answers = {}
    score = 0

    for question in questions:
        selected_id = request.POST.get(
            f"question_{question.id}",
            ""
        )

        correct_choice = question.choices.filter(
            is_correct=True
        ).first()

        selected = (
            question.choices.filter(pk=selected_id).first()
            if selected_id else None
        )

        is_correct = bool(selected and selected.is_correct)

        if is_correct:
            score += 1

        answers[str(question.id)] = {
            "selected_choice_id": selected.pk if selected else None,
            "correct": is_correct,
            "correct_choice_id": (
                correct_choice.pk if correct_choice else None
            ),
        }

    total = len(questions)
    percentage = round(score * 100 / total)
    passed = percentage >= assessment.pass_percentage

    attempt = AssessmentAttempt.objects.create(
        user=request.user,
        assessment=assessment,
        score=score,
        total_questions=total,
        percentage=percentage,
        passed=passed,
        answers=answers,
    )

    return redirect(
        "curriculum:assessment_result",
        attempt_id=attempt.id
    )


@login_required
def assessment_result(request, attempt_id):
    attempt = get_object_or_404(
        AssessmentAttempt.objects.select_related(
            "assessment__section__module__specialization"
        ),
        pk=attempt_id,
        user=request.user,
    )

    questions = list(
        attempt.assessment.questions.prefetch_related("choices")
    )

    result_rows = []

    for question in questions:
        saved = attempt.answers.get(str(question.id), {})
        selected_id = saved.get("selected_choice_id")

        result_rows.append({
            "question": question,
            "selected": (
                question.choices.filter(pk=selected_id).first()
                if selected_id else None
            ),
            "correct_choice": question.choices.filter(
                is_correct=True
            ).first(),
            "is_correct": saved.get("correct", False),
        })

    return render(request, "curriculum/assessment_result.html", {
        "attempt": attempt,
        "result_rows": result_rows,
        "active_page": "learning",
    })


# ============================================================
# MCQ EXAMINATION UNLOCK RULES
# ============================================================

def exam_is_unlocked(user, quiz):
    """
    Lesson exam:
        Available when its lesson is open.

    Module exam:
        All lesson exams in that module must be submitted.

    Course exam 1:
        All lesson and module exams must be submitted.

    Course exam 2:
        Same requirements plus course exam 1.

    Mistake revision:
        Both course exams must be submitted.
    """

    if quiz.exam_type == Quiz.ExamType.LESSON:
        return True

    if quiz.exam_type == Quiz.ExamType.MODULE:
        topic_ids = set(
            Topic.objects.filter(
                section__module=quiz.module,
                section__is_published=True,
                is_published=True
            ).values_list("id", flat=True)
        )

        lesson_quiz_ids = set(
            Quiz.objects.filter(
                topic_id__in=topic_ids,
                exam_type=Quiz.ExamType.LESSON,
                is_published=True
            ).values_list("id", flat=True)
        )

        attempted_ids = set(
            QuizAttempt.objects.filter(
                user=user,
                quiz_id__in=lesson_quiz_ids
            ).values_list("quiz_id", flat=True)
        )

        return lesson_quiz_ids.issubset(attempted_ids)

    if quiz.exam_type in (
        Quiz.ExamType.COURSE_ONE,
        Quiz.ExamType.COURSE_TWO
    ):
        lesson_quiz_ids = set(
            Quiz.objects.filter(
                specialization=quiz.specialization,
                exam_type=Quiz.ExamType.LESSON,
                is_published=True
            ).values_list("id", flat=True)
        )

        module_quiz_ids = set(
            Quiz.objects.filter(
                specialization=quiz.specialization,
                exam_type=Quiz.ExamType.MODULE,
                is_published=True
            ).values_list("id", flat=True)
        )

        attempted_ids = set(
            QuizAttempt.objects.filter(
                user=user,
                quiz_id__in=lesson_quiz_ids | module_quiz_ids
            ).values_list("quiz_id", flat=True)
        )

        required_ids = lesson_quiz_ids | module_quiz_ids

        if not required_ids.issubset(attempted_ids):
            return False

        if quiz.exam_type == Quiz.ExamType.COURSE_TWO:
            first_exam = Quiz.objects.filter(
                specialization=quiz.specialization,
                exam_type=Quiz.ExamType.COURSE_ONE,
                is_published=True
            ).first()

            if first_exam and not QuizAttempt.objects.filter(
                user=user,
                quiz=first_exam
            ).exists():
                return False

        return True

    return True


# ============================================================
# START A ONE-TIME EXAM
# ============================================================

@login_required
def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(
        Quiz.objects.select_related(
            "specialization",
            "module",
            "topic"
        ),
        pk=quiz_id,
        is_published=True,
        specialization__is_published=True
    )

    previous_attempt = QuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz
    ).first()

    # One-time exams cannot be retaken.
    if previous_attempt:
        return redirect(
            "curriculum:quiz_result",
            attempt_id=previous_attempt.id
        )

    if not exam_is_unlocked(request.user, quiz):
        messages.info(
            request,
            "Complete the required lessons and examinations first."
        )
        return redirect(
            "curriculum:specialization_detail",
            slug=quiz.specialization.slug
        )

    questions = list(
        quiz.questions.filter(
            is_active=True
        ).prefetch_related("choices")
    )

    if len(questions) < quiz.question_count:
        messages.error(
            request,
            "This examination is not ready yet. Please contact the administrator."
        )
        return redirect(
            "curriculum:specialization_detail",
            slug=quiz.specialization.slug
        )

    random.shuffle(questions)
    questions = questions[:quiz.question_count]

    question_ids = [question.id for question in questions]

    # Keep the exact question set in the session.
    session_key = f"quiz_{quiz.id}_questions"
    request.session[session_key] = question_ids

    for question in questions:
        choices = list(question.choices.all())
        random.shuffle(choices)
        question.shuffled_choices = choices

        if len(choices) < 2:
            messages.error(
                request,
                "A question does not have enough answer choices."
            )
            return redirect(
                "curriculum:specialization_detail",
                slug=quiz.specialization.slug
            )

    return render(request, "curriculum/quiz_detail.html", {
        "quiz": quiz,
        "questions": questions,
        "active_page": "learning",
    })


# ============================================================
# SUBMIT A ONE-TIME EXAM
# ============================================================

@login_required
@require_POST
@transaction.atomic
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(
        Quiz.objects.select_related("specialization"),
        pk=quiz_id,
        is_published=True,
        specialization__is_published=True
    )

    previous_attempt = QuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz
    ).first()

    if previous_attempt:
        return redirect(
            "curriculum:quiz_result",
            attempt_id=previous_attempt.id
        )

    if not exam_is_unlocked(request.user, quiz):
        messages.error(
            request,
            "This examination is still locked."
        )
        return redirect(
            "curriculum:specialization_detail",
            slug=quiz.specialization.slug
        )

    session_key = f"quiz_{quiz.id}_questions"
    question_ids = request.session.get(session_key)

    if not question_ids:
        messages.error(
            request,
            "Your examination session has expired. Please open the test again."
        )
        return redirect(
            "curriculum:quiz_detail",
            quiz_id=quiz.id
        )

    questions = list(
        QuizQuestion.objects.filter(
            id__in=question_ids,
            quiz=quiz,
            is_active=True
        ).prefetch_related("choices")
    )

    question_map = {
        question.id: question for question in questions
    }

    # Preserve the original displayed order.
    questions = [
        question_map[qid]
        for qid in question_ids
        if qid in question_map
    ]

    if len(questions) != quiz.question_count:
        messages.error(
            request,
            "The examination questions changed. Please restart the test."
        )
        return redirect(
            "curriculum:quiz_detail",
            quiz_id=quiz.id
        )

    score = 0
    saved_answers = {}

    for question in questions:
        selected_id = request.POST.get(
            f"question_{question.id}",
            ""
        )

        selected = (
            question.choices.filter(pk=selected_id).first()
            if selected_id else None
        )

        correct_choice = question.choices.filter(
            is_correct=True
        ).first()

        correct = bool(selected and selected.is_correct)

        if correct:
            score += 1
        else:
            mistake, created = UserQuestionMistake.objects.get_or_create(
                user=request.user,
                question=question,
                defaults={
                    "specialization": quiz.specialization,
                    "wrong_count": 1,
                    "is_resolved": False,
                }
            )

            if not created:
                mistake.wrong_count += 1
                mistake.is_resolved = False
                mistake.resolved_at = None
                mistake.last_wrong_at = timezone.now()
                mistake.save()

        saved_answers[str(question.id)] = {
            "selected_choice_id": selected.pk if selected else None,
            "correct_choice_id": (
                correct_choice.pk if correct_choice else None
            ),
            "correct": correct,
        }

    attempt = QuizAttempt.objects.create(
        user=request.user,
        specialization=quiz.specialization,
        quiz=quiz,
        exam_type=quiz.exam_type,
        question_ids=question_ids,
        answers=saved_answers,
        score=score,
        total_questions=len(questions),
    )

    # Remove session data after successful submission.
    request.session.pop(session_key, None)

    return redirect(
        "curriculum:quiz_result",
        attempt_id=attempt.id
    )


# ============================================================
# EXAMINATION RESULT
# ============================================================

@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related(
            "specialization",
            "quiz"
        ),
        pk=attempt_id,
        user=request.user
    )

    questions = QuizQuestion.objects.filter(
        id__in=attempt.question_ids
    ).prefetch_related("choices")

    question_map = {
        question.id: question for question in questions
    }

    result_rows = []

    for question_id in attempt.question_ids:
        question = question_map.get(question_id)

        if not question:
            continue

        saved = attempt.answers.get(str(question_id), {})

        selected_id = saved.get("selected_choice_id")
        correct_id = saved.get("correct_choice_id")

        result_rows.append({
            "question": question,
            "selected": (
                question.choices.filter(pk=selected_id).first()
                if selected_id else None
            ),
            "correct_choice": (
                question.choices.filter(pk=correct_id).first()
                if correct_id else None
            ),
            "is_correct": saved.get("correct", False),
        })

    return render(request, "curriculum/quiz_result.html", {
        "attempt": attempt,
        "result_rows": result_rows,
        "active_page": "learning",
    })


# ============================================================
# MISTAKE REVISION TEST
# ============================================================

@login_required
def mistake_quiz(request, specialization_slug):
    specialization = get_object_or_404(
        Specialization,
        slug=specialization_slug,
        is_published=True
    )

    # The mistake test is available only after both course exams.
    required_exams = Quiz.objects.filter(
        specialization=specialization,
        exam_type__in=[
            Quiz.ExamType.COURSE_ONE,
            Quiz.ExamType.COURSE_TWO,
        ],
        is_published=True
    )

    required_ids = set(
        required_exams.values_list("id", flat=True)
    )

    submitted_ids = set(
        QuizAttempt.objects.filter(
            user=request.user,
            quiz_id__in=required_ids
        ).values_list("quiz_id", flat=True)
    )

    if required_ids and not required_ids.issubset(submitted_ids):
        messages.info(
            request,
            "Complete both final course examinations before opening the mistake revision test."
        )
        return redirect(
            "curriculum:specialization_detail",
            slug=specialization.slug
        )

    session_key = f"mistake_quiz_{specialization.id}"

    # POST: load exactly the questions saved during GET.
    if request.method == "POST":
        question_ids = request.session.get(session_key)

        if not question_ids:
            messages.error(
                request,
                "Your revision test session has expired. Please start again."
            )
            return redirect(
                "curriculum:mistake_quiz",
                specialization_slug=specialization.slug
            )

        questions = list(
            QuizQuestion.objects.filter(
                id__in=question_ids,
                is_active=True
            ).prefetch_related("choices")
        )

        question_map = {
            question.id: question for question in questions
        }

        questions = [
            question_map[qid]
            for qid in question_ids
            if qid in question_map
        ]

        if len(questions) != len(question_ids):
            messages.error(
                request,
                "Some questions are no longer available. Please start again."
            )
            request.session.pop(session_key, None)
            return redirect(
                "curriculum:mistake_quiz",
                specialization_slug=specialization.slug
            )

        return _submit_mistake_quiz(
            request,
            specialization,
            questions
        )

    # GET: choose unresolved mistakes first.
    mistakes = list(
        UserQuestionMistake.objects.filter(
            user=request.user,
            specialization=specialization,
            is_resolved=False,
            question__is_active=True
        ).select_related("question").values_list(
            "question_id",
            flat=True
        )
    )

    if mistakes:
        question_ids = mistakes
        mode = "mistakes"
    else:
        # No mistakes: create a random practice set.
        question_ids = list(
            QuizQuestion.objects.filter(
                quiz__specialization=specialization,
                quiz__is_published=True,
                is_active=True
            ).values_list("id", flat=True)
        )

        random.shuffle(question_ids)
        question_ids = question_ids[:10]
        mode = "random"

    if not question_ids:
        messages.error(
            request,
            "There are no published questions available for this course yet."
        )
        return redirect(
            "curriculum:specialization_detail",
            slug=specialization.slug
        )

    random.shuffle(question_ids)

    request.session[session_key] = question_ids

    questions = list(
        QuizQuestion.objects.filter(
            id__in=question_ids
        ).prefetch_related("choices")
    )

    question_map = {
        question.id: question for question in questions
    }

    questions = [
        question_map[qid]
        for qid in question_ids
        if qid in question_map
    ]

    for question in questions:
        choices = list(question.choices.all())
        random.shuffle(choices)
        question.shuffled_choices = choices

    return render(request, "curriculum/mistake_quiz.html", {
        "specialization": specialization,
        "questions": questions,
        "mode": mode,
        "active_page": "learning",
    })


# ============================================================
# SUBMIT MISTAKE REVISION TEST
# ============================================================

@transaction.atomic
def _submit_mistake_quiz(request, specialization, questions):
    score = 0
    saved_answers = {}

    for question in questions:
        selected_id = request.POST.get(
            f"question_{question.id}",
            ""
        )

        selected = (
            question.choices.filter(pk=selected_id).first()
            if selected_id else None
        )

        correct_choice = question.choices.filter(
            is_correct=True
        ).first()

        correct = bool(selected and selected.is_correct)

        if correct:
            score += 1

            UserQuestionMistake.objects.filter(
                user=request.user,
                question=question,
                is_resolved=False
            ).update(
                is_resolved=True,
                resolved_at=timezone.now()
            )

        else:
            mistake, created = UserQuestionMistake.objects.get_or_create(
                user=request.user,
                question=question,
                defaults={
                    "specialization": specialization,
                    "wrong_count": 1,
                    "is_resolved": False,
                }
            )

            if not created:
                mistake.wrong_count += 1
                mistake.is_resolved = False
                mistake.resolved_at = None
                mistake.last_wrong_at = timezone.now()
                mistake.save()

        saved_answers[str(question.id)] = {
            "selected_choice_id": selected.pk if selected else None,
            "correct_choice_id": (
                correct_choice.pk if correct_choice else None
            ),
            "correct": correct,
        }

    attempt = QuizAttempt.objects.create(
        user=request.user,
        specialization=specialization,
        quiz=None,
        exam_type=QuizAttempt.ExamType.MISTAKES,
        question_ids=[question.id for question in questions],
        answers=saved_answers,
        score=score,
        total_questions=len(questions),
    )

    request.session.pop(
        f"mistake_quiz_{specialization.id}",
        None
    )

    return redirect(
        "curriculum:quiz_result",
        attempt_id=attempt.id
    )
