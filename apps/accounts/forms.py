from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
User = get_user_model()

class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"autocomplete":"given-name","placeholder":"Your first name"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"autocomplete":"family-name","placeholder":"Your last name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete":"email","placeholder":"you@example.com"}))
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={"autocomplete":"new-password","placeholder":"At least 10 characters"}))
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete":"new-password","placeholder":"Enter password again"}))
    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2") and cleaned["password1"] != cleaned["password2"]:
            self.add_error("password2", "The passwords do not match.")
        if cleaned.get("password1"):
            try: validate_password(cleaned["password1"], User(email=cleaned.get("email",""), first_name=cleaned.get("first_name","")))
            except ValidationError as exc: self.add_error("password1", exc)
        return cleaned

class VerifyEmailForm(forms.Form):
    code = forms.RegexField(regex=r"^\d{6}$", error_messages={"invalid":"Enter the six-digit code."},
        widget=forms.TextInput(attrs={"inputmode":"numeric","autocomplete":"one-time-code","maxlength":"6","placeholder":"000000"}))
class DataForgeAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus":True,"autocomplete":"email","placeholder":"you@example.com"}))
class StyledPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete":"email","placeholder":"you@example.com"}))
class StyledSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(label="New password", widget=forms.PasswordInput(attrs={"autocomplete":"new-password"}))
    new_password2 = forms.CharField(label="Confirm new password", widget=forms.PasswordInput(attrs={"autocomplete":"new-password"}))
