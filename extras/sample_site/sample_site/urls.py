from django.conf.urls import include, url
from django.contrib import admin

from app import views

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^rankedmodel/', include('awl.rankedmodel.urls')),

    url(r'^dform/', include('dform.urls')),
    url(r'^dform_admin/', include('dform.admin_urls')),

    url(r'^embed/', views.embed),
]
