from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .tutor import ask_tutor
@login_required
def tutor(request):
    answer=None;error=None;question=''
    if request.method=='POST':
        question=request.POST.get('question','').strip()
        if question: answer,error=ask_tutor(question)
    return render(request,'collaboration/tutor.html',{'active_page':'tutor','answer':answer,'error':error,'question':question})
