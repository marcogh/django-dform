from django.contrib import admin

from .models import Survey

# ============================================================================

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'version_num')

    def version_num(self, obj):
        return '%s' % obj.latest_version.version_num
    version_num.short_description = 'Latest Version'
