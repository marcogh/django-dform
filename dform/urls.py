from django.conf.urls import patterns, url

urlpatterns = patterns('dform.views',
    url(r'sample_survey/(\d+)/$', 'sample_survey', name='dform-sample-survey'),
    url(r'survey/(\d+)/$', 'survey', name='dform-survey'),
)
