from django.urls import path
from .tutor_views import tutor
urlpatterns=[path('',tutor,name='tutor')]
