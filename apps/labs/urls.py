from django.urls import path
from . import views
app_name="labs"
urlpatterns=[
    path("",views.lab_list,name="list"),
    path("case-studies/",views.case_study_list,name="case_studies"),
    path("case-studies/<slug:slug>/",views.case_study_detail,name="case_study_detail"),
    path("<slug:slug>/submit/",views.submit_lab,name="submit"),
    path("<slug:slug>/draft/",views.save_draft,name="save_draft"),
    path("<slug:slug>/bookmark/",views.toggle_bookmark,name="bookmark"),
    path("<slug:slug>/ai/",views.ai_assist,name="ai_assist"),
    path("<slug:slug>/",views.lab_detail,name="detail"),
]
