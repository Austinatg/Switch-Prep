from datetime import timedelta
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ai_tutor.services import AIServiceError, generate_text

from .models import CaseStudy, Lab, LabAchievement, LabAttempt, LabBookmark, LabDraft
from .services import award_eligible_achievements, evaluate_submission


TRACKS = (
    (Lab.Category.PYTHON, "Python for Data Engineering", "Build dependable ingestion and transformation pipelines."),
    (Lab.Category.SQL, "SQL for Data Engineering", "Query, validate, and model analytical data."),
    (Lab.Category.PYSPARK, "PySpark for Data Engineering", "Transform distributed data with Spark DataFrames."),
)


def _current_streak(user):
    days = set(
        LabAttempt.objects.filter(user=user)
        .values_list("submitted_at__date", flat=True)
        .distinct()
    )
    today = timezone.localdate()
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@login_required
def lab_list(request):
    labs = Lab.objects.filter(is_published=True)
    category = request.GET.get("category", "")
    difficulty = request.GET.get("difficulty", "")
    query = request.GET.get("q", "").strip()
    if category in Lab.Category.values:
        labs = labs.filter(category=category)
    if difficulty in Lab.Difficulty.values:
        labs = labs.filter(difficulty=difficulty)
    if query:
        labs = labs.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(subcategory__icontains=query)
        )

    attempts = LabAttempt.objects.filter(user=request.user).select_related("lab")
    passed_ids = set(
        attempts.filter(status=LabAttempt.Status.PASSED).values_list("lab_id", flat=True)
    )
    attempted_ids = set(attempts.values_list("lab_id", flat=True).distinct())
    total = Lab.objects.filter(is_published=True).count()
    attempted_count = len(attempted_ids)
    solved_count = len(passed_ids)
    total_attempts = attempts.count()
    passed_attempts = attempts.filter(status=LabAttempt.Status.PASSED).count()
    accuracy = round(100 * passed_attempts / total_attempts) if total_attempts else 0

    category_progress = []
    for value, label, _description in TRACKS:
        track_labs = Lab.objects.filter(is_published=True, category=value)
        track_total = track_labs.count()
        track_solved = track_labs.filter(id__in=passed_ids).count()
        category_progress.append(
            {"value": value, "label": label, "total": track_total, "solved": track_solved}
        )
    difficulty_progress = [
        {
            "label": label,
            "total": Lab.objects.filter(is_published=True, difficulty=value).count(),
            "solved": Lab.objects.filter(
                is_published=True, difficulty=value, id__in=passed_ids
            ).count(),
        }
        for value, label in Lab.Difficulty.choices
    ]
    recent_attempts = attempts.order_by("-submitted_at")[:5]
    recommendations = (
        Lab.objects.filter(is_published=True)
        .exclude(id__in=passed_ids)
        .annotate(attempt_count=Count("attempts", filter=Q(attempts__user=request.user)))
        .order_by("attempt_count", "display_order")[:6]
    )
    bookmarked_labs = Lab.objects.filter(
        is_published=True, bookmarks__user=request.user
    ).order_by("bookmarks__created_at")[:6]
    case_studies = CaseStudy.objects.filter(is_published=True)

    page = Paginator(labs, 18).get_page(request.GET.get("page"))
    return render(
        request,
        "labs/list.html",
        {
            "active_page": "labs",
            "labs": page.object_list,
            "solved_lab_ids": passed_ids,
            "page_obj": page,
            "categories": Lab.Category.choices,
            "difficulties": Lab.Difficulty.choices,
            "selected_category": category,
            "selected_difficulty": difficulty,
            "search_query": query,
            "my_attempts": total_attempts,
            "total_questions": total,
            "attempted_count": attempted_count,
            "solved_count": solved_count,
            "accuracy": accuracy,
            "streak": _current_streak(request.user),
            "category_progress": category_progress,
            "difficulty_progress": difficulty_progress,
            "recent_attempts": recent_attempts,
            "recommendations": recommendations,
            "bookmarked_labs": bookmarked_labs,
            "achievements": LabAchievement.objects.filter(user=request.user)[:4],
            "tracks": TRACKS,
            "case_studies": case_studies,
        },
    )


@login_required
def lab_detail(request, slug):
    lab = get_object_or_404(Lab, is_published=True, slug=slug)
    attempts = LabAttempt.objects.filter(user=request.user, lab=lab)[:10]
    draft = LabDraft.objects.filter(user=request.user, lab=lab).first()
    is_bookmarked = LabBookmark.objects.filter(user=request.user, lab=lab).exists()
    return render(
        request,
        "labs/detail.html",
        {
            "active_page": "labs",
            "lab": lab,
            "attempts": attempts,
            "draft": draft,
            "is_bookmarked": is_bookmarked,
            "related_labs": Lab.objects.filter(
                is_published=True, slug__in=lab.related_questions
            ),
        },
    )


@login_required
@require_POST
def submit_lab(request, slug):
    lab = get_object_or_404(Lab, is_published=True, slug=slug)
    answer = request.POST.get("answer", "").strip()
    if not answer:
        messages.error(request, "Add your solution before submitting.")
        return redirect("labs:detail", slug=slug)
    if len(answer) > 50000:
        messages.error(request, "Submissions must be 50,000 characters or fewer.")
        return redirect("labs:detail", slug=slug)

    browser_report = request.POST.get("browser_report")
    if browser_report and lab.execution_mode in {"python", "sql"}:
        try:
            report = json.loads(browser_report)
        except (TypeError, ValueError):
            return JsonResponse({"error": "The browser test report is invalid."}, status=400)
        if not isinstance(report, dict):
            return JsonResponse({"error": "The browser test report is invalid."}, status=400)
        expected_total = (
            max(1, len(lab.public_test_cases or []) + len(lab.hidden_test_cases or []))
            if lab.execution_mode == "python"
            else 1
        )
        total = report.get("total")
        passed_count = report.get("passed_count")
        if (
            report.get("mode") != lab.execution_mode
            or isinstance(total, bool)
            or total != expected_total
            or isinstance(passed_count, bool)
            or not isinstance(passed_count, int)
            or not 0 <= passed_count <= expected_total
        ):
            return JsonResponse({"error": "The browser test report does not match this lab."}, status=400)

        passed = report.get("passed") is True and passed_count == expected_total
        result = {
            "status": LabAttempt.Status.PASSED if passed else LabAttempt.Status.SUBMITTED,
            "score": 100 if passed else round(100 * passed_count / expected_total),
            "feedback": (
                "Congratulations! All browser test cases passed."
                if passed
                else f"{passed_count} of {expected_total} browser test cases passed. Keep trying."
            ),
            "details": {
                "mode": lab.execution_mode,
                "passed_count": passed_count,
                "total": expected_total,
                "verification": "browser_only",
            },
        }
    else:
        result = evaluate_submission(lab, answer)

    LabAttempt.objects.create(
        user=request.user,
        lab=lab,
        answer=answer,
        status=result["status"],
        score=result["score"],
        feedback=result["feedback"],
        evaluation_details=result["details"],
    )
    award_eligible_achievements(request.user)
    if browser_report:
        return JsonResponse(
            {
                "status": result["status"],
                "score": result["score"],
                "feedback": result["feedback"],
                "browser_only": True,
            }
        )
    messages.success(request, f"Submission recorded. {result['feedback']}")
    return redirect("labs:detail", slug=slug)


@login_required
@require_POST
def save_draft(request, slug):
    lab = get_object_or_404(Lab, is_published=True, slug=slug)
    content = request.POST.get("content", "")
    if len(content) > 50000:
        return JsonResponse({"error": "Drafts must be 50,000 characters or fewer."}, status=400)
    draft, _created = LabDraft.objects.update_or_create(
        user=request.user, lab=lab, defaults={"content": content}
    )
    return JsonResponse({"saved": True, "updated_at": draft.updated_at.isoformat()})


@login_required
@require_POST
def toggle_bookmark(request, slug):
    lab = get_object_or_404(Lab, is_published=True, slug=slug)
    bookmark, created = LabBookmark.objects.get_or_create(user=request.user, lab=lab)
    if not created:
        bookmark.delete()
    return JsonResponse({"bookmarked": created})


@login_required
@require_POST
def ai_assist(request, slug):
    lab = get_object_or_404(Lab, is_published=True, slug=slug)
    action = request.POST.get("action", "")
    question = request.POST.get("question", "")[:750]
    code = request.POST.get("code", "")[:1600]
    actions = {
        "explain": "Explain the exercise clearly and accurately, without giving away the complete solution.",
        "hint": "Give one progressive hint, not the complete solution.",
        "review_python": "Review this Python solution for correctness, edge cases, and data-engineering reliability.",
        "review_sql": "Review this SQL query for correctness, dialect caveats, and performance.",
        "explain_pyspark": "Explain the PySpark transformations and their execution implications.",
        "optimize": "Suggest concrete correctness and performance improvements without inventing unsupported APIs.",
        "followups": "Generate three realistic data-engineering interview follow-up questions.",
        "interview": "Conduct one data-engineering interview follow-up question and briefly assess the answer.",
    }
    if action not in actions:
        return JsonResponse({"error": "Choose a supported AI assistant action."}, status=400)
    if action != "explain" and action != "hint" and not code.strip() and not question.strip():
        return JsonResponse({"error": "Add code or a question for the assistant to review."}, status=400)

    prompt = (
        f"Requested help: {actions[action]}\n"
        f"Exercise: {lab.title}\nTrack: {lab.get_category_display()}\n"
        f"Task: {lab.instructions[:700]}\n"
        f"User request: {question}\nCode or query:\n{code}"
    )
    try:
        answer = generate_text(
            prompt,
            "You are a practical Data Engineering interview coach. Be accurate, concise, "
            "and distinguish SQLite-specific behavior from portable SQL. Never claim that "
            "a browser simulation ran Apache Spark.",
            feature="code_assistant",
        )
    except AIServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    return JsonResponse({"answer": answer})


@login_required
def case_study_list(request):
    studies = CaseStudy.objects.filter(is_published=True)
    return render(
        request,
        "labs/case_studies.html",
        {"active_page": "labs", "case_studies": studies},
    )


@login_required
def case_study_detail(request, slug):
    study = get_object_or_404(CaseStudy, is_published=True, slug=slug)
    return render(
        request,
        "labs/case_study_detail.html",
        {"active_page": "labs", "study": study},
    )
