from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import NotePointForm
from .models import DailyNote, NotePoint

def _get_daily_note(user, day):
    note, _ = DailyNote.objects.get_or_create(user=user, learning_date=day, title="")
    return note

@login_required
def notes_home(request):
    today = timezone.localdate()
    query = request.GET.get("q", "").strip()
    selected_date = request.GET.get("date", "").strip()
    try:
        day = date.fromisoformat(selected_date) if selected_date else today
    except ValueError:
        day = today
    daily_note = _get_daily_note(request.user, day)
    points = daily_note.points.all()
    if query:
        points = points.filter(content__icontains=query)
    archive = DailyNote.objects.filter(user=request.user).exclude(learning_date=day).order_by("-learning_date")[:10]
    return render(request, "notes/notes_home.html", {
        "daily_note": daily_note, "points": points, "query": query,
        "selected_date": day.isoformat(), "today": today.isoformat(),
        "archive": archive, "active_page": "notes",
    })

@login_required
@require_POST
def add_point(request):
    day_text = request.POST.get("learning_date", "")
    try: day = date.fromisoformat(day_text) if day_text else timezone.localdate()
    except ValueError: day = timezone.localdate()
    daily_note = _get_daily_note(request.user, day)
    form = NotePointForm(request.POST)
    if form.is_valid():
        point = form.save(commit=False)
        point.daily_note = daily_note
        point.display_order = daily_note.points.count()
        point.save()
        messages.success(request, "Note point added.")
    else:
        messages.error(request, "Please enter a valid note point.")
    return redirect(f"/notes/?date={day.isoformat()}")

@login_required
@require_POST
def quick_add_point(request):
    return_to = (
        request.POST.get("return_to")
        or request.META.get("HTTP_REFERER", "")
    )
    if not url_has_allowed_host_and_scheme(
        return_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return_to = reverse("notes:home")

    daily_note = _get_daily_note(request.user, timezone.localdate())
    form = NotePointForm(request.POST)
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "error": "Please enter a valid note point.",
                "field_errors": form.errors.get_json_data(),
            }, status=400)
        messages.error(request, "Please enter a valid note point.")
        return redirect(return_to)

    point = form.save(commit=False)
    point.daily_note = daily_note
    point.display_order = daily_note.points.count()
    point.save()
    if request.headers.get("x-requested-with") != "XMLHttpRequest":
        messages.success(request, "Note point added.")
        return redirect(return_to)

    return JsonResponse({
        "id": point.pk,
        "content": point.content,
        "importance": point.importance,
        "importance_label": point.get_importance_display(),
        "created_at": timezone.localtime(point.created_at).strftime("%H:%M"),
    }, status=201)

@login_required
def edit_point(request, point_id):
    point = get_object_or_404(NotePoint, pk=point_id, daily_note__user=request.user)
    if request.method == "POST":
        form = NotePointForm(request.POST, instance=point)
        if form.is_valid():
            form.save()
            messages.success(request, "Note point updated.")
            return redirect(f"/notes/?date={point.daily_note.learning_date.isoformat()}")
    else:
        form = NotePointForm(instance=point)
    return render(request, "notes/edit_point.html", {
        "form": form, "point": point, "active_page": "notes",
    })

@login_required
@require_POST
def delete_point(request, point_id):
    point = get_object_or_404(NotePoint, pk=point_id, daily_note__user=request.user)
    day = point.daily_note.learning_date
    point.delete()
    messages.success(request, "Note point deleted.")
    return redirect(f"/notes/?date={day.isoformat()}")

@login_required
def calendar_view(request):
    today = timezone.localdate()
    month_text = request.GET.get("month", "")
    try:
        month = date.fromisoformat(month_text + "-01") if month_text else today.replace(day=1)
    except ValueError:
        month = today.replace(day=1)
    notes = DailyNote.objects.filter(user=request.user).prefetch_related("points")
    month_notes = notes.filter(learning_date__year=month.year, learning_date__month=month.month)
    note_map = {n.learning_date.day: n for n in month_notes}
    first_weekday = month.weekday()
    days_in_month = (date(month.year + (month.month == 12), (month.month % 12) + 1, 1) - timedelta(days=1)).day
    cells = [None] * first_weekday + list(range(1, days_in_month + 1))
    while len(cells) % 7: cells.append(None)
    prev_month = (month.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1).strftime("%Y-%m")
    return render(request, "notes/calendar.html", {
        "month": month, "month_label": month.strftime("%B %Y"), "cells": cells,
        "note_map": note_map, "note_counts": {day: note.points.count() for day, note in note_map.items()}, "prev_month": prev_month, "next_month": next_month,
        "active_page": "calendar",
    })
