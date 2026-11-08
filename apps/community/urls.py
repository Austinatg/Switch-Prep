from django.urls import path
from . import views
app_name='community'
urlpatterns=[
    path('',views.home,name='home'),
    path('connect/<int:user_id>/',views.connect,name='connect'),
    path('request/<int:connection_id>/<str:decision>/',views.respond,name='respond'),
    path('battle/',views.battle,name='battle'),
    path('review/<int:submission_id>/',views.review,name='review'),
    path('notes-calendar/',views.notes_calendar,name='notes_calendar'),
    path('chat/<int:user_id>/',views.chat_with_connection,name='chat'),
]
