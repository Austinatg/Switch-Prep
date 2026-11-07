from django.contrib.auth.decorators import login_required
from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import CertificationTrack,CertificationExam,CertificationAttempt

@login_required
def track_list(request):
    tracks=CertificationTrack.objects.filter(is_published=True).prefetch_related("exams")
    attempts=CertificationAttempt.objects.filter(user=request.user)
    return render(request,"certifications/list.html",{"active_page":"certifications","tracks":tracks,"attempts":attempts[:8],"attempt_count":attempts.count()})

@login_required
def track_detail(request,slug):
    track=get_object_or_404(CertificationTrack,is_published=True,slug=slug)
    return render(request,"certifications/detail.html",{"active_page":"certifications","track":track,"exams":track.exams.filter(is_published=True),"attempts":CertificationAttempt.objects.filter(user=request.user,exam__track=track)[:10]})

@login_required
def exam_detail(request,exam_id):
    exam=get_object_or_404(CertificationExam,pk=exam_id,is_published=True,track__is_published=True)
    return render(request,"certifications/exam.html",{"active_page":"certifications","exam":exam,"questions":exam.questions.prefetch_related("choices")})

@login_required
@require_POST
def submit_exam(request,exam_id):
    exam=get_object_or_404(CertificationExam,pk=exam_id,is_published=True,track__is_published=True)
    questions=list(exam.questions.prefetch_related("choices")); answers={}; score=0
    for q in questions:
        selected=request.POST.get(f"question_{q.pk}","")
        answers[str(q.pk)]=selected
        if selected and q.choices.filter(pk=selected,is_correct=True).exists(): score+=1
    total=len(questions); percentage=round(score*100/total) if total else 0; passed=bool(total) and percentage>=exam.pass_percentage
    attempt=CertificationAttempt.objects.create(user=request.user,exam=exam,score=score,total_questions=total,percentage=percentage,passed=passed,answers=answers)
    return redirect("certifications:result",attempt_id=attempt.pk)

@login_required
def exam_result(request,attempt_id):
    attempt=get_object_or_404(CertificationAttempt.objects.select_related("exam__track"),pk=attempt_id,user=request.user)
    review_rows=[]
    for question in attempt.exam.questions.prefetch_related("choices"):
        choices=list(question.choices.all())
        selected_id=str(attempt.answers.get(str(question.pk), ""))
        review_rows.append({"question":question,"choices":choices,"selected_id":selected_id})
    return render(request,"certifications/result.html",{"active_page":"certifications","attempt":attempt,"review_rows":review_rows})
