from django.conf.urls import url

from dform import views as v

urlpatterns = [
    url(r'^survey_delta/(\d+)/$', v.survey_delta, name='dform-survey-delta'),
    url(r'^survey_editor/(\d+)/$', v.survey_editor, name='dform-edit-survey'),
    url(r'^new_version/(\d+)/$', v.new_version, name='dform-new-version'),

    url(r'^survey_links/(\d+)/$', v.survey_links, name='dform-survey-links'),
    url(r'^answer_links/(\d+)/$', v.answer_links, name='dform-answer-links'),
]
