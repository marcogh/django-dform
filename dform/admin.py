from django.contrib import admin
from django.core.urlresolvers import reverse, NoReverseMatch

from awl.admintools import make_admin_obj_mixin
from awl.rankedmodel.admintools import admin_link_move_up, admin_link_move_down

from .fields import FIELD_CHOICES_DICT
from .models import (Survey, SurveyVersion, Question, QuestionOrder, Answer,
    AnswerGroup)

# ============================================================================

def _questions_link(version, show_reorder=True):
    num_q = Question.objects.filter(survey_versions=version).count()
    if num_q == 0:
        return ''

    plural = ''
    if num_q > 1:
        plural = 's'

    show = reverse('admin:dform_question_changelist')
    reorder = reverse('admin:dform_questionorder_changelist')

    urls = [
        '<a href="%s?survey_versions__id=%s">%s Question%s</a>' % (show, 
            version.id, num_q, plural)
    ]

    if show_reorder:
        urls.append(
            '<a href="%s?survey_version__id=%s">Reorder</a>' % (reorder, 
                version.id)
        )

    return '&nbsp;|&nbsp'.join(urls)


def _answers_link(version):
    num_a = Answer.objects.filter(answer_group__survey_version=version).count()
    if num_a == 0:
        return ''

    plural = ''
    if num_a > 1:
        plural = 's'

    link = reverse('admin:dform_answer_changelist')

    url = '<a href="%s?survey_version__id=%s">%s Answer%s</a>' % (link,
        version.id, num_a, plural)
    return url

# ============================================================================
# Surveys
# ============================================================================

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'version_num', 'show_actions',
        'show_versions', 'show_questions', 'show_answers')

    def version_num(self, obj):
        return '%s' % obj.latest_version.version_num
    version_num.short_description = 'Latest Version'

    def show_actions(self, obj):
        actions = []

        if obj.latest_version.is_editable():
            url = reverse('dform-edit-survey', args=(obj.latest_version.id,))
            actions.append('<a href="%s">Edit Survey</a>' % url)
        else:
            url = reverse('dform-new-version', args=(obj.id,))
            actions.append('<a href="%s">New Version</a>' % url)

        try:
            url = reverse('dform-sample-survey', args=(obj.latest_version.id,))
            actions.append('<a href="%s">View Sample</a>' % url)
        except NoReverseMatch:
            # sample-survey view isn't guaranteed to be there
            pass

        try:
            url = reverse('dform-survey', args=(obj.latest_version.id,))
            actions.append('<a href="%s">Answer Survey</a>' % url)
        except NoReverseMatch:
            # survey view isn't guaranteed to be there
            pass

        return ', '.join(actions)
    show_actions.short_description = 'Actions'
    show_actions.allow_tags = True

    def show_versions(self, obj):
        num_v = SurveyVersion.objects.filter(survey=obj).count()
        link = reverse('admin:dform_surveyversion_changelist')
        url = '<a href="%s?survey__id=%s">%s Versions</a>' % (link, obj.id, 
            num_v)

        return url
    show_versions.short_description = 'Versions'
    show_versions.allow_tags = True

    def show_questions(self, obj):
        return _questions_link(obj.latest_version)
    show_questions.short_description = 'Questions'
    show_questions.allow_tags = True

    def show_answers(self, obj):
        return _answers_link(obj.latest_version)
    show_answers.short_description = 'Answers'
    show_answers.allow_tags = True


mixin = make_admin_obj_mixin('SurveyVersionMixin')
mixin.add_obj_link('show_survey', 'survey')

@admin.register(SurveyVersion)
class SurveyVersionAdmin(admin.ModelAdmin, mixin):
    list_display = ('id', 'show_survey', 'version_num', 'show_actions',
        'show_questions', 'show_answers')

    def show_actions(self, obj):
        actions = []
        if obj.is_editable():
            url = reverse('dform-edit-survey', args=(obj.id,))
            actions.append('<a href="%s">Edit Survey</a>' % url)

        try:
            url = reverse('dform-sample-survey', args=(obj.id,))
            actions.append('<a href="%s">View Sample</a>' % url)
        except NoReverseMatch:
            # view sample isn't guaranteed to be there
            pass

        try:
            url = reverse('dform-survey', args=(obj.id,))
            actions.append('<a href="%s">Answer Survey</a>' % url)
        except NoReverseMatch:
            # survey view isn't guaranteed to be there
            pass

        return ', '.join(actions)
    show_actions.short_description = 'Actions'
    show_actions.allow_tags = True

    def show_questions(self, obj):
        return _questions_link(obj)
    show_questions.short_description = 'Questions'
    show_questions.allow_tags = True

    def show_answers(self, obj):
        return _answers_link(obj)
    show_answers.short_description = 'Answers'
    show_answers.allow_tags = True

# ============================================================================
# Questions
# ============================================================================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'field_key', 'required', 'show_reorder',
        'show_answers')

    def show_reorder(self, obj):
        link = reverse('admin:dform_questionorder_changelist')
        url = '<a href="%s?survey_version__id=%s">Reorder</a>' % (link, 
            obj.survey.latest_version.id)

        return url
    show_reorder.short_description = 'Reorder'
    show_reorder.allow_tags = True

    def show_answers(self, obj):
        num_a = Answer.objects.filter(question=obj).count()
        if num_a == 0:
            return ''

        plural = ''
        if num_a > 1:
            plural = 's'

        link = reverse('admin:dform_answer_changelist')
        url = '<a href="%s?question__id=%s">%s Answer%s</a>'  % (link, obj.id, 
            num_a, plural)
        return url
    show_answers.short_description = 'Answers'
    show_answers.allow_tags = True


@admin.register(QuestionOrder)
class QuestionOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'survey_version', 'show_text', 'move_up',
        'move_down')

    def show_text(self, obj):
        return obj.question.text
    show_text.short_description = 'Question Text'

    def move_up(self, obj):
        return admin_link_move_up(obj, 'Up')
    move_up.allow_tags = True
    move_up.short_description = 'Move Up'

    def move_down(self, obj):
        return admin_link_move_down(obj, 'Down')
    move_down.allow_tags = True
    move_down.short_description = 'Move Down'

# ============================================================================
# Answers
# ============================================================================

mixin = make_admin_obj_mixin('AnswerMixin')
mixin.add_obj_link('show_group', 'answer_group',
    display='AnswerGroup.id={{obj.id}}')
mixin.add_obj_link('show_question', 'question',
    display='Question.id={{obj.id}}')

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin, mixin):
    list_display = ('id', 'show_group', 'show_question', 'show_text', 
        'show_field_key', 'value')

    def show_text(self, obj):
        return obj.question.text
    show_text.short_description = 'Question Text'

    def show_field_key(self, obj):
        return FIELD_CHOICES_DICT[obj.question.field_key]
    show_field_key.short_description = 'Field Key'


mixin = make_admin_obj_mixin('AnswerGroupMixin')
mixin.add_obj_link('show_data', 'group_data')
mixin.add_obj_link('show_version', 'survey_version',
    display='SurveyVersion.id={{obj.id}}')

@admin.register(AnswerGroup)
class AnswerGroupAdmin(admin.ModelAdmin, mixin):
    list_display = ('id', 'updated', 'show_version', 'show_data', 
        'show_questions', 'show_answers', 'show_actions')

    def show_questions(self, obj):
        return _questions_link(obj.survey_version, False)
    show_questions.short_description = 'Questions'
    show_questions.allow_tags = True

    def show_answers(self, obj):
        num_a = Answer.objects.filter(answer_group=obj).count()
        if num_a == 0:
            return ''

        plural = ''
        if num_a > 1:
            plural = 's'

        link = reverse('admin:dform_answer_changelist')

        url = '<a href="%s?answer_group__id=%s">%s Answer%s</a>' % (link,
            obj.id, num_a, plural)
        return url
    show_answers.short_description = 'Answers'
    show_answers.allow_tags = True

    def show_actions(self, obj):
        try:
            url = reverse('dform-survey-with-answers', args=(
                obj.survey_version.id, obj.id))
            return '<a href="%s">Change Answers</a>' % url
        except NoReverseMatch:
            # view survey-with-answers isn't guaranteed to be there
            return ''
    show_actions.short_description = 'Actions'
    show_actions.allow_tags = True
