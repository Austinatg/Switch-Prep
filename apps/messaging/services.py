from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.community.models import Connection

from .models import Conversation


def are_connected(first_user, second_user):
    return Connection.objects.filter(
        Q(sender=first_user, receiver=second_user)
        | Q(sender=second_user, receiver=first_user),
        status=Connection.ACCEPTED,
    ).exists()


def get_direct_conversation(first_user, second_user):
    if not are_connected(first_user, second_user):
        return None

    conversations = (
        Conversation.objects.filter(participants=first_user)
        .filter(participants=second_user)
        .distinct()
    )
    for conversation in conversations:
        if conversation.participants.count() == 2:
            return conversation

    conversation = Conversation.objects.create()
    conversation.participants.add(first_user, second_user)
    return conversation


def get_connected_conversation(user, conversation_id):
    conversation = get_object_or_404(
        Conversation.objects.filter(participants=user),
        pk=conversation_id,
    )
    if conversation.participants.count() != 2:
        raise Http404
    other_user = conversation.participants.exclude(pk=user.pk).first()
    if not other_user or not are_connected(user, other_user):
        raise Http404
    return conversation
