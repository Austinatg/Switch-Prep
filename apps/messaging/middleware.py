from django.utils import timezone
from datetime import timedelta
from .models import UserPresence
class PresenceMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        user=getattr(request,'user',None)
        if user is not None and user.is_authenticated:
            now=timezone.now()
            presence,created=UserPresence.objects.get_or_create(user=user)
            if created or now-presence.last_seen>timedelta(minutes=2):
                UserPresence.objects.filter(pk=presence.pk).update(last_seen=now)
        return response
