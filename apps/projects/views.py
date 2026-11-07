from django.contrib.auth.decorators import login_required
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Project,ProjectEnrollment,MilestoneSubmission,ProjectMilestone

@login_required
def project_list(request):
    projects=Project.objects.filter(is_published=True)
    enrolled=set(ProjectEnrollment.objects.filter(user=request.user).values_list("project_id",flat=True))
    return render(request,"projects/list.html",{"active_page":"projects","projects":projects,"enrolled":enrolled})

@login_required
def project_detail(request,slug):
    project=get_object_or_404(Project,is_published=True,slug=slug)
    enrollment=ProjectEnrollment.objects.filter(user=request.user,project=project).first()
    if request.method=="POST" and not enrollment:
        enrollment=ProjectEnrollment.objects.create(user=request.user,project=project)
        messages.success(request,"You are enrolled in this project. Work through the milestones in order.")
        return redirect("projects:detail",slug=slug)
    submissions=MilestoneSubmission.objects.filter(enrollment=enrollment).select_related("milestone") if enrollment else MilestoneSubmission.objects.none()
    approved=set(submissions.filter(status="approved").values_list("milestone_id",flat=True))
    return render(request,"projects/detail.html",{"active_page":"projects","project":project,"enrollment":enrollment,"submissions":submissions,"approved":approved})

@login_required
@require_POST
def submit_milestone(request,slug,milestone_id):
    project=get_object_or_404(Project,is_published=True,slug=slug)
    enrollment=get_object_or_404(ProjectEnrollment,user=request.user,project=project)
    milestone=get_object_or_404(ProjectMilestone,project=project,pk=milestone_id)
    text=request.POST.get("submission_text","").strip(); url=request.POST.get("artifact_url","").strip()
    if not text and not url:
        messages.error(request,"Add a short explanation or an artifact link before submitting.")
        return redirect("projects:detail",slug=slug)
    MilestoneSubmission.objects.create(enrollment=enrollment,milestone=milestone,submission_text=text,artifact_url=url)
    messages.success(request,"Milestone submitted for review.")
    return redirect("projects:detail",slug=slug)
