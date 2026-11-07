from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .email_service import send_email
from .forms import RegisterForm, VerifyEmailForm
from .models import (
    EmailVerification,
    User,
    UserProfile,
    VerificationCooldownError,
    VerificationRateLimitError,
)

VERIFICATION_SUBJECT = "Verify your SwitchFromTredence account"
DELIVERY_FAILURE_MESSAGE = "We couldn't send your verification email. Please try again."


def _send_verification_email(user, code):
    context = {
        "code": code,
        "expiry_minutes": settings.EMAIL_VERIFICATION_TTL_SECONDS // 60,
    }
    return send_email(
        user.email,
        VERIFICATION_SUBJECT,
        render_to_string("accounts/verification_email.txt", context),
        render_to_string("accounts/verification_email.html", context),
    )


def _show_registration_notice(request, email):
    request.session.pop("pending_verification_user_id", None)
    request.session["registration_notice_only"] = True
    request.session["registration_notice_email"] = email
    messages.info(
        request,
        "If this address is eligible, a verification code will be sent.",
    )
    return redirect("accounts:verify_email")


def _issue_and_send_verification(request, user):
    request.session.pop("registration_notice_only", None)
    request.session.pop("registration_notice_email", None)
    request.session["pending_verification_user_id"] = user.pk
    try:
        _, code = EmailVerification.issue_for(user)
    except VerificationCooldownError:
        messages.info(
            request,
            "If this address is eligible, a verification code will be sent.",
        )
        return
    except VerificationRateLimitError:
        messages.info(
            request,
            "If this address is eligible, a verification code will be sent.",
        )
        return

    result = _send_verification_email(user, code)
    if result.success:
        messages.info(
            request,
            "If this address is eligible, a verification code will be sent.",
        )
    else:
        messages.error(request, DELIVERY_FAILURE_MESSAGE)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.filter(email__iexact=email).first()
            if user and user.is_active:
                return _show_registration_notice(request, email)

            if user is None:
                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            email=email,
                            password=form.cleaned_data["password1"],
                            first_name=form.cleaned_data["first_name"],
                            last_name=form.cleaned_data["last_name"],
                            is_active=False,
                        )
                        UserProfile.objects.get_or_create(user=user)
                except IntegrityError:
                    user = User.objects.filter(email__iexact=email).first()
                    if user is None:
                        raise
                    if user.is_active:
                        return _show_registration_notice(request, email)

            UserProfile.objects.get_or_create(user=user)
            _issue_and_send_verification(request, user)
            return redirect("accounts:verify_email")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def verify_email(request):
    user_id = request.session.get("pending_verification_user_id")
    if not user_id:
        if request.session.get("registration_notice_only"):
            form = VerifyEmailForm(request.POST or None)
            if request.method == "POST" and form.is_valid():
                messages.error(
                    request,
                    "That code is invalid, expired, or has reached its attempt limit.",
                )
            return render(request, "accounts/verify_email.html", {
                "form": form,
                "email": request.session.get("registration_notice_email", ""),
            })
        messages.info(request, "Start by creating an account.")
        return redirect("accounts:register")

    user = User.objects.filter(pk=user_id, is_active=False).first()
    if not user:
        request.session.pop("pending_verification_user_id", None)
        return redirect("accounts:register")

    if request.method == "POST":
        form = VerifyEmailForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                verification = EmailVerification.objects.select_for_update().filter(
                    user=user,
                ).first()
                if verification and verification.check_code(form.cleaned_data["code"]):
                    verification.verified_at = timezone.now()
                    verification.save(update_fields=["verified_at"])
                    user = User.objects.select_for_update().get(pk=user.pk)
                    user.email_verified = True
                    user.is_active = True
                    user.save(update_fields=["email_verified", "is_active"])
                else:
                    verification = None
            if verification:
                request.session.pop("pending_verification_user_id", None)
                login(request, user)
                messages.success(
                    request,
                    "Your email is verified. Welcome to SwitchFromTredence!",
                )
                return redirect("dashboard")
            messages.error(
                request,
                "That code is invalid, expired, or has reached its attempt limit.",
            )
    else:
        form = VerifyEmailForm()
    return render(request, "accounts/verify_email.html", {
        "form": form,
        "email": user.email,
    })


@require_POST
def resend_verification(request):
    user_id = request.session.get("pending_verification_user_id")
    user = User.objects.filter(pk=user_id, is_active=False).first() if user_id else None
    if not user:
        if request.session.get("registration_notice_only"):
            messages.info(
                request,
                "If this address is eligible, a verification code will be sent.",
            )
            return redirect("accounts:verify_email")
        return redirect("accounts:register")

    _issue_and_send_verification(request, user)
    return redirect("accounts:verify_email")


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile_obj.bio = request.POST.get("bio", "")[:280]
        profile_obj.timezone = request.POST.get("timezone", "Asia/Kolkata")[:64]
        profile_obj.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {
        "profile": profile_obj,
        "active_page": "settings",
    })
