from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'admin/', include(admin.site.urls)),

    url(r'rankedmodel/', include('awl.rankedmodel.urls')),

    url(r'dform/', include('dform.urls')),
]
