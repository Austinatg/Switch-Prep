from django.urls import path
from . import views
app_name="certifications"
urlpatterns=[path("",views.track_list,name="list"),path("<slug:slug>/",views.track_detail,name="detail"),path("exams/<int:exam_id>/",views.exam_detail,name="exam"),path("exams/<int:exam_id>/submit/",views.submit_exam,name="submit_exam"),path("results/<int:attempt_id>/",views.exam_result,name="result")]
