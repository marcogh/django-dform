from django.conf.urls import patterns, url

urlpatterns = patterns('ordered_model.views',
    url(r'^sys/ordered_item_up/(\d+)/(\d+)/$', 'ordered_item_up'),
    url(r'^sys/ordered_item_down/(\d+)/(\d+)/$', 'ordered_item_down'),
)
