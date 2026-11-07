import json
from json import JSONDecodeError

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.curriculum.models import Topic, TopicProgress
from apps.labs.models import Lab, LabAttempt

from .forms import (
    CodeAssistantForm,
    InterviewAnswerForm,
    InterviewSetupForm,
    LearningRecommendationForm,
    TutorQuestionForm,
)
from .models import (
    AIConversation,
    AIMessage,
    InterviewQuestion,
    InterviewSession,
)
from .services import (
    AIServiceError,
    generate_text,
)
from .utils import AIUsageLimitError, reserve_ai_request

TUTOR_INSTRUCTIONS = (
    "You are DataForge, a careful Data Engineering tutor. Explain concepts "
    "clearly at the learner's level, state assumptions, and do not claim to "
    "execute code or access systems."
)


def _call_ai(user, prompt, instructions, *, feature, response_mime_type=None):
    if len(prompt) + len(instructions or "") > settings.DATAFORGE_AI_MAX_INPUT_CHARS:
        raise AIServiceError(
            f"Your request must not exceed "
            f"{settings.DATAFORGE_AI_MAX_INPUT_CHARS} characters."
        )
    reserve_ai_request(user)
    return generate_text(
        prompt,
        instructions,
        response_mime_type=response_mime_type,
        feature=feature,
    )


def _show_ai_error(request, error):
    if isinstance(error, AIUsageLimitError):
        messages.warning(request, str(error))
    elif isinstance(error, AIServiceError):
        messages.error(request, str(error))
    else:
        raise error


def _conversation_prompt(conversation, question, level):
    max_chars = max(
        0,
        settings.DATAFORGE_AI_MAX_INPUT_CHARS - len(TUTOR_INSTRUCTIONS),
    )
    question_prefix = f"Explanation level: {level}\nLearner question:\n"
    if len(question) + len(question_prefix) > max_chars:
        raise AIServiceError(
            "Please shorten your question so it fits the lesson context limit."
        )

    parts = []
    remaining = max_chars - len(question_prefix) - len(question)
    if conversation.lesson_context and remaining > 80:
        context_header = f"Lesson context — {conversation.lesson_title}:\n"
        context = conversation.lesson_context[:min(1600, remaining - len(context_header))]
        if context:
            parts.append(context_header + context)
            remaining -= len(context_header) + len(context) + 2

    history = list(
        conversation.messages.order_by("-created_at", "-pk")[:6]
    )
    history.reverse()
    history_lines = []
    for item in history:
        line = f"{item.role.title()}: {item.content}"
        available = remaining - sum(len(value) + 1 for value in history_lines) - 24
        if available <= 0:
            break
        history_lines.append(line[:min(700, available)])
    if history_lines:
        history_text = "Recent conversation:\n" + "\n".join(history_lines)
        if len(history_text) < remaining:
            parts.append(history_text)

    parts.append(question_prefix + question)
    prompt = "\n\n".join(parts)
    if len(prompt) > max_chars:
        raise AIServiceError(
            "This question and its context exceed the request limit. Please shorten it."
        )
    return prompt


def _process_conversation_question(request, conversation, question, level):
    try:
        prompt = _conversation_prompt(conversation, question, level)
        answer = _call_ai(
            request.user,
            prompt,
            TUTOR_INSTRUCTIONS,
            feature="tutor",
        )
    except (AIUsageLimitError, AIServiceError) as error:
        _show_ai_error(request, error)
        return False

    with transaction.atomic():
        AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.USER,
            content=question,
        )
        AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.ASSISTANT,
            content=answer,
        )
        if not conversation.title:
            conversation.title = question[:177] + ("..." if len(question) > 177 else "")
        conversation.explanation_level = level
        conversation.save(update_fields=[
            "title",
            "explanation_level",
            "updated_at",
        ])
    return True


@login_required
def dashboard(request):
    conversations = AIConversation.objects.filter(user=request.user)[:8]
    interviews = InterviewSession.objects.filter(user=request.user)[:5]
    return render(request, "ai_tutor/ai_dashboard.html", {
        "conversations": conversations,
        "interviews": interviews,
        "active_page": "ai_tutor",
    })


@login_required
def tutor(request):
    conversations = AIConversation.objects.filter(user=request.user)[:20]
    return render(request, "ai_tutor/tutor.html", {
        "form": TutorQuestionForm(),
        "conversations": conversations,
        "active_page": "ai_tutor",
    })


@login_required
@require_POST
def new_conversation(request):
    form = TutorQuestionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a question and choose a valid explanation level.")
        return redirect("ai_tutor:tutor")

    conversation = AIConversation.objects.create(user=request.user)
    _process_conversation_question(
        request,
        conversation,
        form.cleaned_data["question"],
        form.cleaned_data["level"],
    )
    return redirect("ai_tutor:conversation", conversation_id=conversation.pk)


@login_required
def lesson_tutor(request, specialization_slug, topic_slug):
    topic = get_object_or_404(
        Topic.objects.select_related("section__module__specialization"),
        slug=topic_slug,
        section__module__specialization__slug=specialization_slug,
        is_published=True,
        section__is_published=True,
        section__module__is_published=True,
        section__module__specialization__is_published=True,
    )
    conversation_id = request.GET.get("conversation")
    if conversation_id:
        conversation = get_object_or_404(
            AIConversation,
            pk=conversation_id,
            user=request.user,
            lesson_reference=f"{specialization_slug}/{topic_slug}",
        )
    else:
        lesson_context = "\n".join(filter(None, [
            topic.summary,
            topic.learning_objectives,
            topic.theory,
            topic.key_takeaways,
        ]))[:3000]
        conversation, created = AIConversation.objects.get_or_create(
            user=request.user,
            lesson_reference=f"{specialization_slug}/{topic_slug}",
            defaults={
                "lesson_title": topic.title,
                "lesson_context": lesson_context,
            },
        )
        if not created:
            conversation.lesson_title = topic.title
            conversation.lesson_context = lesson_context
            conversation.save(update_fields=[
                "lesson_title",
                "lesson_context",
                "updated_at",
            ])
    return redirect("ai_tutor:conversation", conversation_id=conversation.pk)


@login_required
def conversation(request, conversation_id):
    item = get_object_or_404(
        AIConversation,
        pk=conversation_id,
        user=request.user,
    )
    chat_messages = list(item.messages.order_by("-created_at", "-pk")[:80])
    chat_messages.reverse()
    return render(request, "ai_tutor/tutor.html", {
        "form": TutorQuestionForm(),
        "conversation": item,
        "chat_messages": chat_messages,
        "conversations": AIConversation.objects.filter(user=request.user)[:20],
        "active_page": "ai_tutor",
    })


@login_required
@require_POST
def send_message(request, conversation_id):
    item = get_object_or_404(
        AIConversation,
        pk=conversation_id,
        user=request.user,
    )
    form = TutorQuestionForm(request.POST)
    if form.is_valid():
        _process_conversation_question(
            request,
            item,
            form.cleaned_data["question"],
            form.cleaned_data["level"],
        )
    else:
        messages.error(request, "Please enter a question and choose a valid explanation level.")
    return redirect("ai_tutor:conversation", conversation_id=item.pk)


@login_required
@require_POST
def delete_conversation(request, conversation_id):
    item = get_object_or_404(
        AIConversation,
        pk=conversation_id,
        user=request.user,
    )
    item.delete()
    messages.success(request, "Conversation deleted.")
    return redirect("ai_tutor:tutor")


@login_required
def code_assistant(request):
    answer = None
    form = CodeAssistantForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        prompt = (
            f"Language: {data['language']}\n"
            f"Task: {data['task']}\n"
            f"Instructions: {data['instructions']}\n"
            f"Code:\n{data['code']}"
        )
        try:
            answer = _call_ai(
                request.user,
                prompt,
                "You are a code assistant. Analyze submitted code as text only. "
                "Never execute it. Explain assumptions and provide safe, focused suggestions.",
                feature="code_assistant",
            )
        except (AIUsageLimitError, AIServiceError) as error:
            _show_ai_error(request, error)
    return render(request, "ai_tutor/code_assistant.html", {
        "form": form,
        "answer": answer,
        "active_page": "code_assistant",
    })


@login_required
def learning_path(request):
    form = LearningRecommendationForm(request.POST or None)
    answer = None
    has_progress = False
    if request.method == "POST" and form.is_valid():
        topics = list(Topic.objects.filter(
            is_published=True,
            section__is_published=True,
            section__module__is_published=True,
            section__module__specialization__is_published=True,
        ).select_related("section__module__specialization").order_by(
            "section__module__display_order",
            "section__display_order",
            "display_order",
        )[:70])
        progress = {
            entry.topic_id: entry
            for entry in TopicProgress.objects.filter(
                user=request.user,
                topic__in=topics,
            ).only("topic_id", "is_completed", "last_opened_at")
        }
        has_progress = bool(progress)
        topic_lines = []
        for topic in topics:
            entry = progress.get(topic.pk)
            state = (
                "completed" if entry and entry.is_completed
                else "in progress" if entry
                else "not started"
            )
            last_opened = (
                timezone.localtime(entry.last_opened_at).strftime("%Y-%m-%d")
                if entry else "not recorded"
            )
            topic_lines.append(
                f"{topic.title} | {topic.difficulty} | {state} | "
                f"last opened {last_opened} | "
                f"{topic.section.module.specialization.name}"
            )

        recent_lab_attempts = LabAttempt.objects.filter(
            user=request.user,
            lab__is_published=True,
        ).select_related("lab").order_by("-submitted_at")[:10]
        lab_lines = [
            f"{attempt.lab.title} | {attempt.lab.category} | "
            f"{attempt.status} | score {attempt.score}"
            for attempt in recent_lab_attempts
        ]
        published_labs = Lab.objects.filter(is_published=True).order_by(
            "display_order", "title"
        )[:30]
        lab_options = [f"{lab.title} | {lab.category} | {lab.difficulty}" for lab in published_labs]
        interests = form.cleaned_data["interests"].strip()
        prompt = (
            "Recommend a realistic next learning sequence from this published curriculum. "
            "Use the progress and lab data exactly as supplied; do not invent completed work. "
            "If progress is absent, clearly label recommendations as general. Include "
            "a recommended next lesson, a practice lab when available, topics to revise, "
            "a suggested learning sequence, and a short reason for each recommendation. "
            f"\nLearner interests: {interests or 'not supplied'}"
            f"\nProgress available: {'yes' if has_progress else 'no'}"
            f"\nLessons:\n" + "\n".join(topic_lines)
            + "\nRecent lab attempts:\n" + "\n".join(lab_lines)
            + "\nAvailable practice labs:\n" + "\n".join(lab_options)
        )
        instructions = (
            "You are a personalized Data Engineering learning coach. "
            "Recommend only lessons and labs included in the provided lists. "
            "Never claim progress that is not present."
        )
        prompt = prompt[:max(
            0,
            settings.DATAFORGE_AI_MAX_INPUT_CHARS - len(instructions),
        )]
        try:
            answer = _call_ai(
                request.user,
                prompt,
                instructions,
                feature="personalized_learning",
            )
        except (AIUsageLimitError, AIServiceError) as error:
            _show_ai_error(request, error)

    return render(request, "ai_tutor/learning_path.html", {
        "form": form,
        "answer": answer,
        "has_progress": has_progress,
        "active_page": "personalized_learning",
    })


@login_required
def interview_setup(request):
    form = InterviewSetupForm()
    history = InterviewSession.objects.filter(user=request.user)[:10]
    return render(request, "ai_tutor/interview_setup.html", {
        "form": form,
        "history": history,
        "active_page": "interview_simulator",
    })


def _json_from_response(response):
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except JSONDecodeError as error:
        raise AIServiceError(
            "The AI service returned an unreadable response. Please try again."
        ) from error


@login_required
@require_POST
def start_interview(request):
    form = InterviewSetupForm(request.POST)
    if not form.is_valid():
        for error in form.errors.get("__all__", []):
            messages.error(request, error)
        messages.error(request, "Choose an interview category, difficulty, and length.")
        return redirect("ai_tutor:interview_setup")

    category = form.cleaned_data["category"]
    difficulty = form.cleaned_data["difficulty"]
    total_questions = form.cleaned_data["total_questions"]
    prompt = (
        f"Create exactly {total_questions} concise Data Engineering interview questions "
        f"for category {category} at {difficulty} difficulty. Return only a JSON array "
        'of strings, with no answers or markdown.'
    )
    try:
        response = _call_ai(
            request.user,
            prompt,
            "Generate original, clear interview questions. Return the exact requested "
            "number in the requested JSON format.",
            feature="interview_simulator.question_generation",
            response_mime_type="application/json",
        )
        questions = _json_from_response(response)
        if (
            not isinstance(questions, list)
            or len(questions) != total_questions
            or any(
                not isinstance(question, str)
                or not question.strip()
                or len(question) > 500
                for question in questions
            )
        ):
            raise AIServiceError(
                "The AI service could not create a complete interview. Please try again."
            )
    except (AIUsageLimitError, AIServiceError) as error:
        _show_ai_error(request, error)
        return redirect("ai_tutor:interview_setup")

    with transaction.atomic():
        session = InterviewSession.objects.create(
            user=request.user,
            category=category,
            difficulty=difficulty,
            total_questions=total_questions,
        )
        InterviewQuestion.objects.bulk_create([
            InterviewQuestion(
                session=session,
                question_text=question.strip(),
                question_number=index,
            )
            for index, question in enumerate(questions, start=1)
        ])
    return redirect("ai_tutor:interview", session_id=session.pk)


@login_required
def interview(request, session_id):
    session = get_object_or_404(
        InterviewSession.objects.prefetch_related("questions"),
        pk=session_id,
        user=request.user,
    )
    if session.status == InterviewSession.Status.COMPLETED:
        return redirect("ai_tutor:interview_result", session_id=session.pk)
    current = get_object_or_404(
        InterviewQuestion,
        session=session,
        question_number=session.current_question,
    )
    previous = None
    if current.question_number > 1:
        previous = session.questions.filter(
            question_number=current.question_number - 1
        ).first()
    form = InterviewAnswerForm()
    return render(request, "ai_tutor/interview.html", {
        "session": session,
        "question": current,
        "previous_question": previous,
        "form": form,
        "active_page": "interview_simulator",
    })


@login_required
@require_POST
def submit_interview_answer(request, session_id, question_number):
    session = get_object_or_404(
        InterviewSession,
        pk=session_id,
        user=request.user,
        status=InterviewSession.Status.ACTIVE,
    )
    if question_number != session.current_question:
        raise Http404
    question = get_object_or_404(
        InterviewQuestion,
        session=session,
        question_number=session.current_question,
    )
    form = InterviewAnswerForm(request.POST)
    if not form.is_valid():
        for error in form.errors.get("answer", form.non_field_errors()):
            messages.error(request, error)
        return redirect("ai_tutor:interview", session_id=session.pk)
    if question.user_answer:
        messages.info(request, "This answer has already been submitted.")
        return redirect("ai_tutor:interview", session_id=session.pk)

    answer = form.cleaned_data["answer"]
    with transaction.atomic():
        question = InterviewQuestion.objects.select_for_update().get(pk=question.pk)
        if question.user_answer or question.is_evaluating:
            messages.info(request, "This answer is already being processed.")
            return redirect("ai_tutor:interview", session_id=session.pk)
        question.is_evaluating = True
        question.save(update_fields=["is_evaluating"])

    prompt = (
        "Evaluate the candidate's answer to the interview question. Return only a JSON "
        "object with integer score from 0 to 10 and string fields explanation, strengths, "
        "weaknesses, and improved_answer.\n"
        f"Question: {question.question_text}\nCandidate answer: {answer}"
    )
    try:
        response = _call_ai(
            request.user,
            prompt,
            "Evaluate fairly and constructively. Do not require one exact wording. "
            "Score technical correctness, completeness, and clarity. Return valid JSON.",
            feature="interview_simulator.answer_evaluation",
            response_mime_type="application/json",
        )
        evaluation = _json_from_response(response)
        if not isinstance(evaluation, dict):
            raise AIServiceError("The AI service returned an invalid evaluation.")
        try:
            raw_score = evaluation.get("score", -1)
            if isinstance(raw_score, bool):
                raise ValueError
            score = int(raw_score)
        except (TypeError, ValueError):
            raise AIServiceError(
                "The AI service returned an invalid evaluation score."
            ) from None
        if not 0 <= score <= 10:
            raise AIServiceError("The AI service returned an invalid evaluation score.")
        for field in ("explanation", "strengths", "weaknesses", "improved_answer"):
            if not isinstance(evaluation.get(field), str):
                evaluation[field] = ""
        evaluation["score"] = score
    except (AIUsageLimitError, AIServiceError) as error:
        InterviewQuestion.objects.filter(
            pk=question.pk,
            is_evaluating=True,
        ).update(is_evaluating=False)
        _show_ai_error(request, error)
        return redirect("ai_tutor:interview", session_id=session.pk)

    with transaction.atomic():
        locked_question = InterviewQuestion.objects.select_for_update().get(
            pk=question.pk,
            is_evaluating=True,
        )
        locked_question.user_answer = answer
        locked_question.is_evaluating = False
        locked_question.evaluation = evaluation
        locked_question.score = score
        locked_question.save(update_fields=["user_answer", "evaluation", "score"])
    return redirect("ai_tutor:interview", session_id=session.pk)


@login_required
@require_POST
def next_interview_question(request, session_id):
    with transaction.atomic():
        session = get_object_or_404(
            InterviewSession.objects.select_for_update(),
            pk=session_id,
            user=request.user,
            status=InterviewSession.Status.ACTIVE,
        )
        current = get_object_or_404(
            InterviewQuestion,
            session=session,
            question_number=session.current_question,
        )
        if not current.user_answer:
            messages.error(request, "Submit your answer before continuing.")
            return redirect("ai_tutor:interview", session_id=session.pk)

        if session.current_question >= session.total_questions:
            total = sum(question.score for question in session.questions.all())
            session.total_score = round(total * 100 / (session.total_questions * 10))
            session.status = InterviewSession.Status.COMPLETED
            session.completed_at = timezone.now()
            session.save(update_fields=[
                "total_score", "status", "completed_at",
            ])
            return redirect("ai_tutor:interview_result", session_id=session.pk)

        session.current_question += 1
        session.save(update_fields=["current_question"])
    return redirect("ai_tutor:interview", session_id=session.pk)


@login_required
def interview_result(request, session_id):
    session = get_object_or_404(
        InterviewSession.objects.prefetch_related("questions"),
        pk=session_id,
        user=request.user,
    )
    if session.status != InterviewSession.Status.COMPLETED:
        return redirect("ai_tutor:interview", session_id=session.pk)
    return render(request, "ai_tutor/interview_result.html", {
        "session": session,
        "active_page": "interview_simulator",
    })


@login_required
def interview_history(request):
    sessions = InterviewSession.objects.filter(user=request.user)
    return render(request, "ai_tutor/interview_setup.html", {
        "history": sessions,
        "history_only": True,
        "active_page": "interview_simulator",
    })
