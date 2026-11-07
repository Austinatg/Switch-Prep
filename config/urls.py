from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def home(request):
    return redirect("dashboard") if request.user.is_authenticated else render(request, "home.html")

@login_required
def dashboard(request):
    return render(request, "dashboard/index.html", {"active_page": "dashboard"})

@login_required
def workspace_page(request, page):
    page_data = {
        "learning": ("Learning paths", "Choose a specialization and follow a structured Data Engineering roadmap.", "graduation-cap"),
        "labs": ("Labs & projects", "Hands-on exercises, milestone projects and enterprise capstones will live here.", "flask"),
        "certifications": ("Certifications", "Prepare for current cloud and data platform certification exams.", "award"),
        "notes": ("My notes", "Capture individual learning points, mark their importance and revisit them by date.", "notebook-pen"),
        "calendar": ("Learning calendar", "Review your daily learning activity and archived notes.", "calendar-days"),
        "community": ("Connections & battles", "Connect with learners and challenge each other with daily questions.", "users"),
        "messages": ("Messages", "Your private conversations and live chat will appear here.", "message-circle"),
        "tutor": ("AI Data Engineering tutor", "Ask questions about SQL, Python, Spark, cloud platforms and data architecture.", "bot"),
        "settings": ("Settings", "Manage your profile and account preferences.", "settings"),
    }
    title, description, icon = page_data.get(page, ("Workspace", "This section is being prepared.", "layers"))
    return render(request, "dashboard/placeholder.html", {
        "active_page": page, "page_title": title, "page_description": description, "page_icon": icon
    })

def health(request):
    return JsonResponse({"status": "ok", "service": "dataforge"})

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("workspace/<slug:page>/", workspace_page, name="workspace"),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("learning/", include("apps.curriculum.urls")),
    path("notes/", include("apps.notes.urls")),
    path("labs/", include("apps.labs.urls")),
    path("projects/", include("apps.projects.urls")),
    path("certifications/", include("apps.certifications.urls")),
    path("community/", include("apps.community.urls")),
    path("shared-learning/", include("apps.collaboration.urls")),
    path("messages/", include("apps.messaging.urls")),
    path("tutor/", include("apps.collaboration.tutor_urls")),
]
