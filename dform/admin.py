from django.contrib import admin
from django.core.urlresolvers import reverse

from awl.admintools import make_admin_obj_mixin

from .models import Survey, SurveyVersion

# ============================================================================

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'version_num', 'show_actions')

    def version_num(self, obj):
        return '%s' % obj.latest_version.version_num
    version_num.short_description = 'Latest Version'

    def show_actions(self, obj):
        if obj.latest_version.is_editable():
            url = reverse('dform-edit-survey', args=(obj.latest_version.id,))
            return '<a href="%s">Edit Survey</a>' % url
        else:
            url = reverse('dform-new-version', args=(obj.id,))
            return '<a href="%s">New Version</a>' % url
    show_actions.short_description = 'Actions'
    show_actions.allow_tags = True


mixin = make_admin_obj_mixin('SurveyVersionMixin')
mixin.add_obj_link('show_survey', 'survey')

@admin.register(SurveyVersion)
class SurveyVersionAdmin(admin.ModelAdmin, mixin):
    list_display = ('id', 'show_survey', 'version_num', 'show_actions')

    def show_actions(self, obj):
        if obj.is_editable():
            url = reverse('dform-edit-survey', args=(obj.id,))
            return '<a href="%s">Edit Survey</a>' % url
        else:
            ''
    show_actions.short_description = 'Actions'
    show_actions.allow_tags = True
