from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Connection,DailyBattle,BattleSubmission,BattleAnswer,PeerReview
User=get_user_model()
@login_required
def home(request):
    q=request.GET.get('q','').strip()
    people=User.objects.exclude(pk=request.user.pk).filter(is_active=True)
    if q: people=people.filter(Q(first_name__icontains=q)|Q(last_name__icontains=q)|Q(email__icontains=q))
    links=Connection.objects.filter(Q(sender=request.user)|Q(receiver=request.user)).select_related('sender','receiver')
    sent=set(links.filter(sender=request.user).values_list('receiver_id',flat=True)); received=set(links.filter(receiver=request.user).values_list('sender_id',flat=True))
    return render(request,'community/home.html',{'active_page':'community','people':people[:30],'connections':links,'sent_ids':sent,'received_ids':received})
@login_required
@require_POST
def connect(request,user_id):
    target=get_object_or_404(User,pk=user_id,is_active=True)
    if target==request.user: messages.error(request,'You cannot connect with yourself.')
    else:
        existing=Connection.objects.filter(Q(sender=request.user,receiver=target)|Q(sender=target,receiver=request.user)).first()
        if not existing:
            Connection.objects.create(sender=request.user,receiver=target)
            from apps.messaging.models import Notification
            Notification.objects.create(user=target,actor=request.user,message='sent you a connection request',target_url='/community/')
            messages.success(request,'Connection request sent.')
        elif existing.status=='declined': existing.sender=request.user;existing.receiver=target;existing.status='pending';existing.save();messages.success(request,'Connection request sent again.')
        else: messages.info(request,'A connection request already exists.')
    return redirect('community:home')
@login_required
@require_POST
def respond(request,connection_id,decision):
    item=get_object_or_404(Connection,pk=connection_id,receiver=request.user,status='pending')
    if decision not in ('accept','decline'): return redirect('community:home')
    item.status='accepted' if decision=='accept' else 'declined';item.save(update_fields=['status','updated_at'])
    if decision=='accept':
        from apps.messaging.models import Notification
        Notification.objects.create(user=item.sender,actor=request.user,message='accepted your connection request',target_url='/community/')
    messages.success(request,'Connection updated.');return redirect('community:home')
@login_required
def battle(request):
    today=timezone.localdate(); battle=DailyBattle.objects.filter(battle_date=today,is_published=True).first()
    submission=BattleSubmission.objects.filter(battle=battle,user=request.user).first() if battle else None
    if request.method=='POST' and battle and not submission:
        questions=list(battle.questions.all())
        if len(questions)!=5: messages.error(request,'The daily battle is being prepared. Please check back later.')
        elif all(request.POST.get(f'answer_{q.pk}','').strip() for q in questions):
            submission=BattleSubmission.objects.create(battle=battle,user=request.user)
            BattleAnswer.objects.bulk_create([BattleAnswer(submission=submission,question=q,answer_text=request.POST.get(f'answer_{q.pk}','').strip()) for q in questions])
            messages.success(request,'Your five answers have been submitted. Peer review will be available when another learner reviews them.')
        else: messages.error(request,'Please answer all five questions before submitting.')
        return redirect('community:battle')
    peer_submissions=[]
    if battle:
        peer_submissions=BattleSubmission.objects.filter(battle=battle).exclude(user=request.user).filter(Q(user__sent_connections__receiver=request.user,user__sent_connections__status='accepted')|Q(user__received_connections__sender=request.user,user__received_connections__status='accepted')).select_related('user').prefetch_related('answers__question')
    leaderboard=[]
    if battle:
        from django.db.models import Count
        leaderboard=list(BattleSubmission.objects.filter(battle=battle).annotate(review_count=Count('reviews')).select_related('user').order_by('-review_count','submitted_at')[:10])
    return render(request,'community/battle.html',{'active_page':'community','battle':battle,'submission':submission,'questions':battle.questions.all() if battle else [],'leaderboard':leaderboard,'peer_submissions':peer_submissions})
@login_required
@require_POST
def review(request,submission_id):
    target=get_object_or_404(BattleSubmission,pk=submission_id)
    if target.user_id==request.user.id: messages.error(request,'You cannot review your own submission.')
    elif not Connection.objects.filter(Q(sender=request.user,receiver=target.user)|Q(sender=target.user,receiver=request.user),status='accepted').exists(): messages.error(request,'Peer reviews are limited to accepted connections.')
    else:
        score=max(0,min(5,int(request.POST.get('score','0')))); PeerReview.objects.update_or_create(submission=target,reviewer=request.user,defaults={'score':score,'feedback':request.POST.get('feedback','')[:500]})
        from apps.messaging.models import Notification
        Notification.objects.create(user=target.user,actor=request.user,message='reviewed your daily battle submission',target_url='/community/battle/')
        messages.success(request,'Peer review saved.')
    return redirect('community:battle')
