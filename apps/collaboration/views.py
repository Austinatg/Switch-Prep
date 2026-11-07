from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from .models import SharedNotebook,SharedNote,NoteComment

def can_access(notebook,user): return notebook.owner_id==user.id or notebook.members.filter(pk=user.pk).exists() or notebook.is_public
@login_required
def home(request):
    notebooks=SharedNotebook.objects.filter(Q(owner=request.user)|Q(members=request.user)|Q(is_public=True)).distinct().select_related('owner')
    if request.method=='POST':
        title=request.POST.get('title','').strip()
        if title: SharedNotebook.objects.create(owner=request.user,title=title[:180],description=request.POST.get('description','')[:2000]);messages.success(request,'Collaborative notebook created.')
        return redirect('collaboration:home')
    return render(request,'collaboration/home.html',{'active_page':'community','notebooks':notebooks})
@login_required
def detail(request,notebook_id):
    notebook=get_object_or_404(SharedNotebook,pk=notebook_id)
    if not can_access(notebook,request.user): return redirect('collaboration:home')
    if request.method=='POST':
        title=request.POST.get('title','').strip();content=request.POST.get('content','').strip()
        if title and content: SharedNote.objects.create(notebook=notebook,author=request.user,title=title[:180],content=content);notebook.save(update_fields=['updated_at']);messages.success(request,'Note added.')
        return redirect('collaboration:detail',notebook_id=notebook.pk)
    return render(request,'collaboration/detail.html',{'active_page':'community','notebook':notebook,'notes':notebook.notes.select_related('author').prefetch_related('comments__author')})
@login_required
@require_POST
def comment(request,note_id):
    note=get_object_or_404(SharedNote,pk=note_id); notebook=note.notebook
    if can_access(notebook,request.user):
        body=request.POST.get('body','').strip()
        if body: NoteComment.objects.create(note=note,author=request.user,body=body[:2000]);messages.success(request,'Comment added.')
    return redirect('collaboration:detail',notebook_id=notebook.pk)
@login_required
@require_POST
def invite(request,notebook_id):
    notebook=get_object_or_404(SharedNotebook,pk=notebook_id,owner=request.user)
    email=request.POST.get('email','').strip().lower()
    from django.contrib.auth import get_user_model
    User=get_user_model(); person=User.objects.filter(email=email,is_active=True).first()
    if person and person!=request.user: notebook.members.add(person);messages.success(request,'Learner added to the notebook.')
    else: messages.error(request,'No active learner found with that email.')
    return redirect('collaboration:detail',notebook_id=notebook.pk)

@login_required
@require_POST
def compile_notebook(request,notebook_id):
    notebook=get_object_or_404(SharedNotebook,pk=notebook_id)
    if not can_access(notebook,request.user): return redirect('collaboration:home')
    from .tutor import ask_tutor
    source='\n\n'.join(f'{n.title}\n{n.content}' for n in notebook.notes.all()[:30])
    if not source.strip():
        messages.error(request,'Add some notes before compiling them.')
    else:
        result,error=ask_tutor(request.user, 'Compile these collaborative notes into a clear, structured study guide. Preserve technical details, group related concepts, highlight contradictions or missing information, and do not invent facts.\n\n'+source)
        if error: messages.error(request,error)
        else: SharedNote.objects.create(notebook=notebook,author=request.user,title='AI compiled study guide',content=result);notebook.save(update_fields=['updated_at']);messages.success(request,'AI study guide added to this notebook.')
    return redirect('collaboration:detail',notebook_id=notebook.pk)
