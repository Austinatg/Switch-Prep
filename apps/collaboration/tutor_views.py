from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def tutor(request):
    return redirect("ai_tutor:tutor")
