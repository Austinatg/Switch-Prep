from django.urls import path
from . import views
app_name = "notes"
urlpatterns = [
    path("", views.notes_home, name="home"),
    path("add/", views.add_point, name="add"),
    path("quick-add/", views.quick_add_point, name="quick_add"),
    path("point/<int:point_id>/edit/", views.edit_point, name="edit"),
    path("point/<int:point_id>/delete/", views.delete_point, name="delete"),
    path("calendar/", views.calendar_view, name="calendar"),
]
