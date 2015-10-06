from django.conf.urls import include, url
from django.contrib import admin

from dform import urls as dform_urls

urlpatterns = [
    url(r'admin/', include(admin.site.urls)),

    url(r'dform/', include(dform_urls)),
]
