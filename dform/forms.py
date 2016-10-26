# dform.forms.py
from django import forms
from django.template.loader import render_to_string

from .fields import (ChoiceField, Rating, MultipleChoicesStorage, Integer, 
    Float)
from .models import Answer, AnswerGroup, Question

# ============================================================================

class SurveyForm(forms.Form):
    """Used to marshal survey answers.  Members that may be useful to access
    are:

    :param survey_version: :class:`.SurveyVersion` object that was used to
        create this form
    :param answer_group: :class:`.AnswerGroup` object that references the
        stored questions and answers for the form
    """
    def __init__(self, *args, **kwargs):
        self.survey_version = kwargs.pop('survey_version')
        self.answer_group = kwargs.pop('answer_group', None)
        self.ip_address = kwargs.pop('ip_address', '')

        if 'initial' in kwargs:
            raise AttributeError(
                '"initial" keyword is not allowed with SurveyForm')

        super(SurveyForm, self).__init__(*args, **kwargs)

        # populate any answers from the database
        values = {}
        if self.answer_group:
            for answer in self.answer_group.answer_set.all():
                key = 'q_%s' % answer.question.id
                values[key] = answer.value

        # update values with info from a POST if passed in
        if len(args) > 0:
            values.update(args[0])

        self.populate_fields(values)

    def populate_fields(self, values):
        for question in self.survey_version.questions():
            name = 'q_%s' % question.id

            kwargs = {
                'label':question.text,
                'required':question.required,
            }

            if name in values:
                kwargs['initial'] = values[name]

            if question.field.django_widget:
                kwargs['widget'] = question.field.django_widget

            if question.field == Rating:
                kwargs['choices'] = (
                    (5, '5 Star'),
                    (4, '4 Star'),
                    (3, '3 Star'),
                    (2, '2 Star'),
                    (1, '1 Star'),
                )
            elif issubclass(question.field, ChoiceField):
                kwargs['choices'] = question.field_choices()

            field = question.field.django_field(**kwargs)
            field.question = question
            if question.field.form_control:
                field.widget.attrs['class'] = 'form-control'

            self.fields[name] = field

    def render_form(self):
        return render_to_string('dform/fields.html', {'form':self})

    def save(self):
        if not self.answer_group:
            self.answer_group = AnswerGroup.factory(
                survey_version=self.survey_version)

        if self.ip_address:
            self.answer_group.ip_address = self.ip_address
            self.answer_group.save()

        for name, field in self.fields.items():
            question = Question.objects.get(id=name[2:], 
                survey_versions=self.survey_version)

            value = self.cleaned_data[name]
            if not value:
                # value is empty, remove any existing answers and otherwise
                # ignore it
                try:
                    # check for an existing Answer that should now be removed
                    answer = Answer.objects.get(question=question,
                        answer_group=self.answer_group)
                    answer.delete()
                except Answer.DoesNotExist:
                    # no answer to remove, do nothing
                    pass
            else:
                if question.field in [Rating, Integer]:
                    value = int(value)
                elif question.field == Float:
                    value = float(value)
                elif issubclass(question.field, MultipleChoicesStorage):
                    value = ','.join(value)

                self.survey_version.answer_question(question, 
                    self.answer_group, value)

    def has_required(self):
        for field in self.fields.values():
            if field.required:
                return True

        return False
