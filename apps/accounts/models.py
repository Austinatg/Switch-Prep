import hashlib, secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models, transaction
from django.utils import timezone

class UserManager(BaseUserManager):
    use_in_migrations = True
    def _create_user(self, email, password, **extra_fields):
        if not email: raise ValueError("An email address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False); extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True); extra_fields.setdefault("is_superuser", True); extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    email_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]
    objects = UserManager()
    def __str__(self): return self.email

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    bio = models.CharField(max_length=280, blank=True)
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"Profile: {self.user.email}"

class VerificationCooldownError(Exception):
    pass


class VerificationRateLimitError(Exception):
    pass


class EmailVerification(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_verification")
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_sent_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveSmallIntegerField(default=0)
    send_window_started_at = models.DateTimeField(default=timezone.now)
    send_count = models.PositiveSmallIntegerField(default=1)
    verified_at = models.DateTimeField(null=True, blank=True)
    MAX_ATTEMPTS = 5
    MAX_SENDS_PER_HOUR = 5

    @staticmethod
    def hash_code(code): return hashlib.sha256(code.encode()).hexdigest()

    @classmethod
    def issue_for(cls, user):
        now = timezone.now()
        with transaction.atomic():
            locked_user = type(user).objects.select_for_update().get(pk=user.pk)
            obj = cls.objects.select_for_update().filter(user=locked_user).first()
            if obj:
                if now - obj.last_sent_at < timedelta(
                    seconds=settings.EMAIL_VERIFICATION_RESEND_SECONDS
                ):
                    raise VerificationCooldownError
                if now - obj.send_window_started_at >= timedelta(hours=1):
                    obj.send_window_started_at = now
                    obj.send_count = 0
                if obj.send_count >= cls.MAX_SENDS_PER_HOUR:
                    raise VerificationRateLimitError
            else:
                obj = cls(
                    user=locked_user,
                    send_window_started_at=now,
                    send_count=0,
                )

            code = f"{secrets.randbelow(1_000_000):06d}"
            obj.code_hash = cls.hash_code(code)
            obj.created_at = now
            obj.expires_at = now + timedelta(
                seconds=settings.EMAIL_VERIFICATION_TTL_SECONDS
            )
            obj.last_sent_at = now
            obj.attempts = 0
            obj.verified_at = None
            obj.send_count += 1
            obj.save()
        return obj, code

    def is_expired(self): return timezone.now() >= self.expires_at

    def check_code(self, code):
        if (
            self.verified_at
            or self.is_expired()
            or self.attempts >= self.MAX_ATTEMPTS
        ):
            return False
        self.attempts += 1
        valid = secrets.compare_digest(self.code_hash, self.hash_code(code.strip()))
        self.save(update_fields=["attempts"])
        return valid

    def __str__(self): return f"Email verification for {self.user.email}"
