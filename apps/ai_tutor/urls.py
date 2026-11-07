from django.urls import path

from . import views

app_name = "ai_tutor"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tutor/", views.tutor, name="tutor"),
    path("tutor/new/", views.new_conversation, name="new_conversation"),
    path("tutor/<int:conversation_id>/", views.conversation, name="conversation"),
    path(
        "tutor/<int:conversation_id>/send/",
        views.send_message,
        name="send_message",
    ),
    path(
        "tutor/<int:conversation_id>/delete/",
        views.delete_conversation,
        name="delete_conversation",
    ),
    path(
        "lesson/<slug:specialization_slug>/<slug:topic_slug>/",
        views.lesson_tutor,
        name="lesson_tutor",
    ),
    path("code/", views.code_assistant, name="code_assistant"),
    path("learning/", views.learning_path, name="learning_path"),
    path("interviews/", views.interview_setup, name="interview_setup"),
    path("interviews/start/", views.start_interview, name="start_interview"),
    path("interviews/history/", views.interview_history, name="interview_history"),
    path(
        "interviews/<int:session_id>/",
        views.interview,
        name="interview",
    ),
    path(
        "interviews/<int:session_id>/answer/<int:question_number>/",
        views.submit_interview_answer,
        name="submit_interview_answer",
    ),
    path(
        "interviews/<int:session_id>/next/",
        views.next_interview_question,
        name="next_interview_question",
    ),
    path(
        "interviews/<int:session_id>/result/",
        views.interview_result,
        name="interview_result",
    ),
]
