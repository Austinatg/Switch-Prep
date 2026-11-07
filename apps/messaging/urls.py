from django.urls import path
from . import views
app_name='messaging'
urlpatterns=[path('',views.inbox,name='inbox'),path('notifications/',views.notifications,name='notifications'),path('<int:conversation_id>/',views.chat,name='chat'),path('<int:conversation_id>/send/',views.send_message,name='send'),path('<int:conversation_id>/poll/',views.poll_messages,name='poll')]
