from django.conf.urls import patterns, url

urlpatterns = patterns('dform.views',
    url(r'^sample_survey/(\d+)/$', 'sample_survey', name='dform-sample-survey'),

    url(r'^survey/(\d+)/(\w+)/$', 'survey', name='dform-survey'),
    url(r'^embedded_survey/(\d+)/(\w+)/$', 'embedded_survey', 
      name='dform-embedded-survey'),

    url(r'^survey_with_answers/(\d+)/(\w+)/(\d+)/(\w+)/$', 
        'survey_with_answers', name='dform-survey-with-answers'),
    url(r'^embedded_survey_with_answers/(\d+)/(\w+)/(\d+)/(\w+)/$', 
        'embedded_survey_with_answers', 
        name='dform-embedded-survey-with-answers'),
)
