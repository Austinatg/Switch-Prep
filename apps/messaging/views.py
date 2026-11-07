import json
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from apps.community.models import Connection
from .models import Conversation,Message
User=get_user_model()
def connected(a,b): return Connection.objects.filter(Q(sender=a,receiver=b)|Q(sender=b,receiver=a),status='accepted').exists()
@login_required
def inbox(request):
    conversations=Conversation.objects.filter(participants=request.user).prefetch_related('participants','messages')
    people=User.objects.filter(Q(sent_connections__receiver=request.user,sent_connections__status='accepted')|Q(received_connections__sender=request.user,received_connections__status='accepted')).distinct()
    if request.method=='POST':
        other=get_object_or_404(User,pk=request.POST.get('user_id'))
        if connected(request.user,other):
            conv=Conversation.objects.filter(participants=request.user).filter(participants=other).first()
            if not conv:
                conv=Conversation.objects.create();conv.participants.add(request.user,other)
            return redirect('messaging:chat',conversation_id=conv.pk)
        return redirect('messaging:inbox')
    return render(request,'messaging/inbox.html',{'active_page':'messages','conversations':conversations,'people':people})
@login_required
def chat(request,conversation_id):
    conv=get_object_or_404(Conversation,pk=conversation_id,participants=request.user)
    other=conv.participants.exclude(pk=request.user.pk).first()
    conv.messages.exclude(sender=request.user).exclude(read_by=request.user).update() if False else None
    for msg in conv.messages.exclude(sender=request.user): msg.read_by.add(request.user)
    return render(request,'messaging/chat.html',{'active_page':'messages','conversation':conv,'other':other,'chat_messages':conv.messages.select_related('sender')})
@login_required
@require_POST
def send_message(request,conversation_id):
    conv=get_object_or_404(Conversation,pk=conversation_id,participants=request.user)
    body=request.POST.get('body','').strip()
    if body:
        msg=Message.objects.create(conversation=conv,sender=request.user,body=body[:5000]);conv.save(update_fields=['updated_at'])
        from .models import Notification
        recipient=conv.participants.exclude(pk=request.user.pk).first()
        if recipient: Notification.objects.create(user=recipient,actor=request.user,message='sent you a message',target_url='/messages/'+str(conv.pk)+'/')
        return JsonResponse({'ok':True,'id':msg.pk,'body':msg.body,'sender':request.user.first_name or request.user.email,'created_at':timezone.localtime(msg.created_at).strftime('%H:%M')})
    return JsonResponse({'ok':False,'error':'Message cannot be empty.'},status=400)
@login_required
def poll_messages(request,conversation_id):
    conv=get_object_or_404(Conversation,pk=conversation_id,participants=request.user)
    after=int(request.GET.get('after','0') or 0)
    rows=conv.messages.filter(pk__gt=after).exclude(sender=request.user).select_related('sender')[:100]
    data=[{'id':m.pk,'body':m.body,'sender':m.sender.first_name or m.sender.email,'created_at':timezone.localtime(m.created_at).strftime('%H:%M')} for m in rows]
    for m in rows: m.read_by.add(request.user)
    return JsonResponse({'messages':data})

@login_required
def notifications(request):
    from .models import Notification
    rows=Notification.objects.filter(user=request.user)[:100]
    Notification.objects.filter(user=request.user,is_read=False).update(is_read=True)
    return render(request,'messaging/notifications.html',{'active_page':'messages','notifications':rows})
