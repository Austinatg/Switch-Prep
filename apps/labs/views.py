from django.contrib.auth.decorators import login_required
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Lab,LabAttempt
from .services import evaluate_submission

@login_required
def lab_list(request):
    labs=Lab.objects.filter(is_published=True)
    category=request.GET.get("category","")
    if category in Lab.Category.values: labs=labs.filter(category=category)
    return render(request,"labs/list.html",{"active_page":"labs","labs":labs,"categories":Lab.Category.choices,"selected_category":category,"my_attempts":LabAttempt.objects.filter(user=request.user).count()})

@login_required
def lab_detail(request,slug):
    lab=get_object_or_404(Lab,is_published=True,slug=slug)
    attempts=LabAttempt.objects.filter(user=request.user,lab=lab)[:10]
    return render(request,"labs/detail.html",{"active_page":"labs","lab":lab,"attempts":attempts})

@login_required
@require_POST
def submit_lab(request,slug):
    lab=get_object_or_404(Lab,is_published=True,slug=slug)
    answer=request.POST.get("answer","").strip()
    if not answer:
        messages.error(request,"Add your solution before submitting.")
        return redirect("labs:detail",slug=slug)
    result=evaluate_submission(lab,answer)
    attempt=LabAttempt.objects.create(user=request.user,lab=lab,answer=answer,status=result["status"],score=result["score"],feedback=result["feedback"],evaluation_details=result["details"])
    messages.success(request,f"Submission recorded. {result['feedback']}")
    return redirect("labs:detail",slug=slug)
