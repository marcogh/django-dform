from django.conf.urls import url
from dform import views

urlpatterns = [
    url(r'^sample_survey/(\d+)/$', views.sample_survey, 
        name='dform-sample-survey'),

    url(r'^survey/(\d+)/(\w+)/$', views.survey, name='dform-survey'),
    url(r'^embedded_survey/(\d+)/(\w+)/$', views.embedded_survey, 
      name='dform-embedded-survey'),

    url(r'^survey_latest/(\d+)/(\w+)/$', views.survey_latest, 
        name='dform-survey-latest'),
    url(r'^embedded_survey_latest/(\d+)/(\w+)/$', views.embedded_survey_latest, 
      name='dform-embedded-survey-latest'),

    url(r'^survey_with_answers/(\d+)/(\w+)/(\d+)/(\w+)/$', 
        views.survey_with_answers, name='dform-survey-with-answers'),
    url(r'^embedded_survey_with_answers/(\d+)/(\w+)/(\d+)/(\w+)/$', 
        views.embedded_survey_with_answers, 
        name='dform-embedded-survey-with-answers'),
]
