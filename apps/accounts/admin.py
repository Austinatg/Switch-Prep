from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import UserProfile, EmailVerification
User=get_user_model()
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering=("email",); list_display=("email","first_name","last_name","email_verified","is_staff","is_active")
    list_filter=("email_verified","is_staff","is_active"); search_fields=("email","first_name","last_name")
    fieldsets=((None,{"fields":("email","password")}),("Personal info",{"fields":("first_name","last_name","email_verified")}),
    ("Permissions",{"fields":("is_active","is_staff","is_superuser","groups","user_permissions")}),("Important dates",{"fields":("last_login","date_joined")}))
    add_fieldsets=((None,{"classes":("wide",),"fields":("email","first_name","password1","password2","is_staff","is_superuser")}),)
    filter_horizontal=("groups","user_permissions"); readonly_fields=("date_joined","last_login")
admin.site.register(UserProfile)
admin.site.register(EmailVerification)
