from django.urls import path
from . import views
app_name="labs"
urlpatterns=[path("",views.lab_list,name="list"),path("<slug:slug>/",views.lab_detail,name="detail"),path("<slug:slug>/submit/",views.submit_lab,name="submit")]
