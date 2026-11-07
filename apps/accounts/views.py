from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from .forms import RegisterForm, VerifyEmailForm
from .models import User, UserProfile, EmailVerification

def register(request):
    if request.user.is_authenticated: return redirect("dashboard")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(email=form.cleaned_data["email"], password=form.cleaned_data["password1"],
                    first_name=form.cleaned_data["first_name"], last_name=form.cleaned_data["last_name"], is_active=False)
                UserProfile.objects.create(user=user)
                verification, code = EmailVerification.issue_for(user)
            send_mail("Your DataForge verification code",
                f"Your DataForge verification code is {code}. It expires in {settings.EMAIL_VERIFICATION_TTL_SECONDS // 60} minutes.",
                settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
            request.session["pending_verification_user_id"] = user.pk
            messages.success(request, "We sent a six-digit verification code to your email.")
            return redirect("accounts:verify_email")
    else: form = RegisterForm()
    return render(request, "accounts/register.html", {"form":form})

def verify_email(request):
    user_id = request.session.get("pending_verification_user_id")
    if not user_id:
        messages.info(request, "Start by creating an account."); return redirect("accounts:register")
    user = User.objects.filter(pk=user_id, is_active=False).first()
    if not user:
        request.session.pop("pending_verification_user_id", None); return redirect("accounts:login")
    if request.method == "POST":
        form = VerifyEmailForm(request.POST)
        if form.is_valid():
            verification = EmailVerification.objects.filter(user=user).first()
            if verification and verification.check_code(form.cleaned_data["code"]):
                verification.verified_at = timezone.now(); verification.save(update_fields=["verified_at"])
                user.email_verified = True; user.is_active = True; user.save(update_fields=["email_verified","is_active"])
                request.session.pop("pending_verification_user_id", None); login(request,user)
                messages.success(request,"Your email is verified. Welcome to DataForge!"); return redirect("dashboard")
            messages.error(request,"That code is invalid, expired, or has reached its attempt limit.")
    else: form = VerifyEmailForm()
    return render(request,"accounts/verify_email.html",{"form":form,"email":user.email})

def resend_verification(request):
    user_id = request.session.get("pending_verification_user_id")
    user = User.objects.filter(pk=user_id,is_active=False).first() if user_id else None
    if not user: return redirect("accounts:register")
    verification = EmailVerification.objects.filter(user=user).first()
    if verification and timezone.now()-verification.last_sent_at < timedelta(seconds=settings.EMAIL_VERIFICATION_RESEND_SECONDS):
        messages.warning(request,"Please wait before requesting another code."); return redirect("accounts:verify_email")
    verification,code = EmailVerification.issue_for(user)
    send_mail("Your new DataForge verification code",f"Your new verification code is {code}.",settings.DEFAULT_FROM_EMAIL,[user.email],fail_silently=False)
    messages.success(request,"A new verification code has been sent."); return redirect("accounts:verify_email")

@login_required
def profile(request):
    profile_obj,_ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile_obj.bio=request.POST.get("bio","")[:280]
        profile_obj.timezone=request.POST.get("timezone","Asia/Kolkata")[:64]
        profile_obj.save(); messages.success(request,"Profile updated."); return redirect("accounts:profile")
    return render(request,"accounts/profile.html",{"profile":profile_obj,"active_page":"settings"})
