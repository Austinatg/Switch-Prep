from django.urls import path
from . import views
app_name='collaboration'
urlpatterns=[path('',views.home,name='home'),path('<int:notebook_id>/',views.detail,name='detail'),path('comment/<int:note_id>/',views.comment,name='comment'),path('<int:notebook_id>/invite/',views.invite,name='invite'),path('<int:notebook_id>/compile/',views.compile_notebook,name='compile')]
