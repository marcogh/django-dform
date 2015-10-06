from django.conf.urls import patterns, url

urlpatterns = patterns('dform.views',
    url(r'survey_delta/(\d+)/$', 'survey_delta'),
)
