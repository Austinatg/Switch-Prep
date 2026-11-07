from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AIGlobalUsage, AIUsage


class AIUsageLimitError(Exception):
    pass


def reserve_ai_request(user):
    today = timezone.localdate()
    user_limit = max(0, int(settings.DATAFORGE_AI_DAILY_LIMIT))
    global_limit = max(0, int(settings.DATAFORGE_AI_GLOBAL_DAILY_LIMIT))

    with transaction.atomic():
        usage, _ = AIUsage.objects.get_or_create(user=user, date=today)
        global_usage, _ = AIGlobalUsage.objects.get_or_create(date=today)
        usage = AIUsage.objects.select_for_update().get(pk=usage.pk)
        global_usage = AIGlobalUsage.objects.select_for_update().get(
            pk=global_usage.pk
        )

        if usage.request_count >= user_limit or global_usage.request_count >= global_limit:
            raise AIUsageLimitError("AI usage limit reached. Please try again later.")

        usage.request_count += 1
        global_usage.request_count += 1
        usage.save(update_fields=["request_count"])
        global_usage.save(update_fields=["request_count"])
