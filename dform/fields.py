# dform.fields.py
import logging

from django.core.exceptions import ValidationError
from django.forms import fields
from django.forms import widgets

logger = logging.getLogger(__name__)

# ============================================================================

class Field(object):
    django_widget = ''
    form_control = True

    @classmethod
    def check_field_parms(cls, field_parms):
        if field_parms:
            raise ValidationError('%s field does not take parameters' % (
                cls.__name__))


class ChoiceField(Field):
    @classmethod
    def check_field_parms(cls, field_parms):
        if len(field_parms) < 1 or not isinstance(field_parms, dict):
            raise ValidationError(('%s field expected a dict of valid '
                'choices') % cls.__name__)

# ============================================================================
# Storage Types
# ============================================================================

class TextStorage(object):
    storage_key = 'answer_text'

    @classmethod
    def check_value(cls, field_parms, value):
        pass


class ChoicesStorage(object):
    storage_key = 'answer_key'

    @classmethod
    def check_value(cls, field_parms, value):
        if value not in field_parms:
            raise ValidationError('value was not in available choices')


class MultipleChoicesStorage(object):
    storage_key = 'answer_key'

    @classmethod
    def check_value(cls, field_parms, value):
        keys = value.split(',')
        for key in keys:
            if key not in field_parms:
                raise ValidationError('value was not in available choices')


class NumberStorage(object):
    storage_key = 'answer_float'

    @classmethod
    def check_value(cls, field_parms, value):
        try:
            float(value)
        except ValueError:
            raise ValidationError('value was not numeric')

# ============================================================================
# Field Types
# ============================================================================

class Text(Field, TextStorage):
    field_key = 'tx'
    template = 'dform/fields/text.html'
    django_field = fields.CharField


class MultiText(Field, TextStorage):
    field_key = 'mt'
    template = 'dform/fields/multitext.html'
    django_field = fields.CharField
    django_widget = widgets.Textarea


class Dropdown(ChoiceField, ChoicesStorage):
    field_key = 'dr'
    template = 'dform/fields/dropdown.html'
    django_field = fields.ChoiceField
    django_widget = widgets.Select


class Radio(ChoiceField, ChoicesStorage):
    field_key = 'rd'
    template = 'dform/fields/radio.html'
    django_field = fields.ChoiceField
    django_widget = widgets.RadioSelect
    form_control = False


class Checkboxes(ChoiceField, MultipleChoicesStorage):
    field_key = 'ch'
    template = 'dform/fields/checkboxes.html'
    django_field = fields.ChoiceField
    django_widget = widgets.CheckboxSelectMultiple
    form_control = False


class Rating(Field, NumberStorage):
    field_key = 'rt'
    template = 'dform/fields/rating.html'
    django_field = fields.ChoiceField
    django_widget = widgets.RadioSelect

# ============================================================================

FIELDS = [Text, MultiText, Dropdown, Radio, Checkboxes, Rating]
FIELDS_DICT = {f.field_key:f for f in FIELDS}
FIELD_CHOICES = [(f.field_key, f.__name__) for f in FIELDS]
FIELD_CHOICES_DICT = dict(FIELD_CHOICES)
