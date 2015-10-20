# dform.forms.py
from django import forms
from django.template.loader import render_to_string

from .fields import (FIELDS_DICT, ChoiceField, Rating, MultipleChoicesStorage,
    Integer, Float)
from .models import AnswerGroup, Question

# ============================================================================

class SurveyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.survey_version = kwargs.pop('survey_version')
        self.answer_group = kwargs.pop('answer_group', None)

        if 'initial' in kwargs:
            raise AttributeError(
                '"initial" keyword is not allowed with SurveyForm')

        super(SurveyForm, self).__init__(*args, **kwargs)

        # populate any answers from the database
        values = {}
        if self.answer_group:
            for answer in self.answer_group.answer_set.all():
                key = 'q_%s' % answer.question.id
                if isinstance(answer.question.field, MultipleChoicesStorage):
                    values[key] = answer.value.split(',')
                else:
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
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += ' form-control'
                else:
                    field.widget.attrs['class'] = 'form-control'

            self.fields[name] = field

    def render_form(self):
        return render_to_string('dform/fields.html', {'form':self})

    def save(self):
        if not self.answer_group:
            self.answer_group = AnswerGroup.objects.create(
                survey_version=self.survey_version)

        for name, field in self.fields.items():
            question = Question.objects.get(id=name[2:], 
                survey_versions=self.survey_version)

            value = self.cleaned_data[name]
            if not value and not question.required:
                continue

            if question.field in [Rating, Integer]:
                value = int(value)
            elif question.field == Float:
                value = float(value)
            elif issubclass(question.field, MultipleChoicesStorage):
                value = ','.join(value)

            self.survey_version.answer_question(question, self.answer_group, 
                value)

    def has_required(self):
        for field in self.fields.values():
            if field.required:
                return True

        return False
