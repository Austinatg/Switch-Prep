from pathlib import PurePath

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Conversation, Message
from .services import get_connected_conversation, get_direct_conversation

User = get_user_model()

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".pdf", ".txt", ".csv", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx",
}


def _message_data(message, viewer):
    return {
        "id": message.pk,
        "body": message.body,
        "sender": message.sender.get_full_name() or message.sender.email,
        "is_own": message.sender_id == viewer.pk,
        "created_at": timezone.localtime(message.created_at).strftime("%H:%M"),
        "attachment_name": message.attachment_name,
        "attachment_url": (
            reverse("messaging:download", args=[message.pk])
            if message.attachment
            else ""
        ),
    }


@login_required
def inbox(request):
    conversations = (
        Conversation.objects.filter(participants=request.user)
        .prefetch_related("participants", "messages")
        .order_by("-updated_at")
    )
    people = User.objects.filter(
        Q(sent_connections__receiver=request.user, sent_connections__status="accepted")
        | Q(received_connections__sender=request.user, received_connections__status="accepted")
    ).distinct()
    if request.method == "POST":
        other = get_object_or_404(User, pk=request.POST.get("user_id"))
        conversation = get_direct_conversation(request.user, other)
        if conversation:
            return redirect("messaging:chat", conversation_id=conversation.pk)
        return redirect("messaging:inbox")
    return render(
        request,
        "messaging/inbox.html",
        {
            "active_page": "messages",
            "conversations": conversations,
            "people": people,
        },
    )


@login_required
def chat(request, conversation_id):
    conversation = get_connected_conversation(request.user, conversation_id)
    other = conversation.participants.exclude(pk=request.user.pk).first()
    unread_messages = conversation.messages.exclude(sender=request.user).exclude(
        read_by=request.user
    )
    for message in unread_messages:
        message.read_by.add(request.user)
    return render(
        request,
        "messaging/chat.html",
        {
            "active_page": "messages",
            "other": other,
            "conversation": conversation,
            "chat_messages": conversation.messages.select_related("sender"),
            "allowed_extensions": ",".join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS)),
        },
    )


@login_required
@require_POST
def send_message(request, conversation_id):
    conversation = get_connected_conversation(request.user, conversation_id)
    body = request.POST.get("body", "").strip()
    attachment = request.FILES.get("attachment")

    if len(body) > 5000:
        return JsonResponse({"ok": False, "error": "Messages are limited to 5,000 characters."}, status=400)
    if not body and not attachment:
        return JsonResponse({"ok": False, "error": "Write a message or choose a file to attach."}, status=400)
    if attachment:
        extension = PurePath(attachment.name).suffix.lower()
        if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "That file type is not supported. Attach an image, PDF, text/CSV, or Office document.",
                },
                status=400,
            )
        if attachment.size > MAX_ATTACHMENT_SIZE:
            return JsonResponse(
                {"ok": False, "error": "Attachments must be 10 MB or smaller."},
                status=400,
            )

    attachment_name = ""
    if attachment:
        attachment_name = PurePath(attachment.name.replace("\\", "/")).name[:255]
    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        body=body,
        attachment=attachment or "",
        attachment_name=attachment_name,
    )
    conversation.save(update_fields=["updated_at"])
    recipient = conversation.participants.exclude(pk=request.user.pk).first()
    if recipient:
        from .models import Notification

        Notification.objects.create(
            user=recipient,
            actor=request.user,
            message="sent you a message",
            target_url=f"/messages/{conversation.pk}/",
        )
    return JsonResponse({"ok": True, **_message_data(message, request.user)})


@login_required
def poll_messages(request, conversation_id):
    conversation = get_connected_conversation(request.user, conversation_id)
    try:
        after = max(0, int(request.GET.get("after", "0") or 0))
    except ValueError:
        return JsonResponse({"error": "Invalid message cursor."}, status=400)

    rows = list(
        conversation.messages.filter(pk__gt=after)
        .exclude(sender=request.user)
        .select_related("sender")[:100]
    )
    data = [_message_data(message, request.user) for message in rows]
    for message in rows:
        message.read_by.add(request.user)
    return JsonResponse({"messages": data})


@login_required
def download_attachment(request, message_id):
    message = get_object_or_404(
        Message.objects.select_related("conversation", "sender"),
        pk=message_id,
    )
    get_connected_conversation(request.user, message.conversation_id)
    if not message.attachment:
        raise Http404
    try:
        attachment = message.attachment.open("rb")
    except FileNotFoundError:
        raise Http404 from None
    response = FileResponse(
        attachment,
        as_attachment=True,
        filename=message.attachment_name or "attachment",
        content_type="application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def notifications(request):
    from .models import Notification

    rows = Notification.objects.filter(user=request.user)[:100]
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(
        request,
        "messaging/notifications.html",
        {"active_page": "messages", "notifications": rows},
    )
