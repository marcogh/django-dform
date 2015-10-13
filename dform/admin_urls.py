from django.conf.urls import patterns, url

urlpatterns = patterns('dform.views',
    url(r'survey_delta/(\d+)/$', 'survey_delta', name='dform-survey-delta'),
    url(r'survey_editor/(\d+)/$', 'survey_editor', name='dform-edit-survey'),
    url(r'new_version/(\d+)/$', 'new_version', name='dform-new-version'),
)
