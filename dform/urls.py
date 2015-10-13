from django.conf.urls import patterns, url

urlpatterns = patterns('dform.views',
    url(r'sample_form/(\d+)/$', 'sample_form', ),
)
