
from django.urls import path
from . import views

app_name = "curriculum"

urlpatterns = [
    # Curriculum
    path(
        "",
        views.specialization_list,
        name="specialization_list"
    ),
    path(
        "<slug:slug>/",
        views.specialization_detail,
        name="specialization_detail"
    ),
    path(
        "<slug:specialization_slug>/topics/<slug:topic_slug>/",
        views.topic_detail,
        name="topic_detail"
    ),

    # Topic progress and bookmarks
    path(
        "progress/<int:topic_id>/toggle/",
        views.toggle_topic_completion,
        name="toggle_topic_completion"
    ),
    path(
        "bookmarks/<int:topic_id>/toggle/",
        views.toggle_bookmark,
        name="toggle_bookmark"
    ),

    # Existing section assessments
    path(
        "assessments/<int:assessment_id>/",
        views.assessment_detail,
        name="assessment_detail"
    ),
    path(
        "assessments/<int:assessment_id>/submit/",
        views.submit_assessment,
        name="submit_assessment"
    ),
    path(
        "assessment-attempts/<int:attempt_id>/",
        views.assessment_result,
        name="assessment_result"
    ),

    # New MCQ examinations
    path(
        "quizzes/<int:quiz_id>/",
        views.quiz_detail,
        name="quiz_detail"
    ),
    path(
        "quizzes/<int:quiz_id>/submit/",
        views.submit_quiz,
        name="submit_quiz"
    ),
    path(
        "quiz-attempts/<int:attempt_id>/",
        views.quiz_result,
        name="quiz_result"
    ),

    # Mistake revision
    path(
        "<slug:specialization_slug>/mistake-test/",
        views.mistake_quiz,
        name="mistake_quiz"
    ),
]
