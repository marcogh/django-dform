from django.conf.urls import patterns, url

urlpatterns = patterns('dform.views',
    url(r'sample_survey/(\d+)/$', 'sample_survey', name='dform-sample-survey'),
    url(r'survey/(\d+)/$', 'survey', name='dform-survey'),
    url(r'survey_with_answers/(\d+)/(\d+)/$', 'survey_with_answers', 
        name='dform-survey-with-answers'),
)
