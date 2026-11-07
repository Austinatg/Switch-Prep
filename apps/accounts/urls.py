from django.contrib.auth import views as auth_views
from django.urls import path
from .forms import DataForgeAuthenticationForm, StyledPasswordResetForm, StyledSetPasswordForm
from . import views
app_name="accounts"
urlpatterns=[
 path("register/",views.register,name="register"),
 path("verify-email/",views.verify_email,name="verify_email"),
 path("resend-verification/",views.resend_verification,name="resend_verification"),
 path("login/",auth_views.LoginView.as_view(template_name="accounts/login.html",authentication_form=DataForgeAuthenticationForm),name="login"),
 path("logout/",auth_views.LogoutView.as_view(),name="logout"),
 path("password-reset/",auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html",email_template_name="accounts/password_reset_email.txt",form_class=StyledPasswordResetForm,success_url="/accounts/password-reset/done/"),name="password_reset"),
 path("password-reset/done/",auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),name="password_reset_done"),
 path("reset/<uidb64>/<token>/",auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html",form_class=StyledSetPasswordForm,success_url="/accounts/reset/done/"),name="password_reset_confirm"),
 path("reset/done/",auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),name="password_reset_complete"),
 path("profile/",views.profile,name="profile"),
]
