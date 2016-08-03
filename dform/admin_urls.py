from django.conf.urls import patterns, url

urlpatterns = patterns('dform.views',
    url(r'^survey_delta/(\d+)/$', 'survey_delta', name='dform-survey-delta'),
    url(r'^survey_editor/(\d+)/$', 'survey_editor', name='dform-edit-survey'),
    url(r'^new_version/(\d+)/$', 'new_version', name='dform-new-version'),

    url(r'^survey_links/(\d+)/$', 'survey_links', name='dform-survey-links'),
    url(r'^answer_links/(\d+)/$', 'answer_links', name='dform-answer-links'),
)
