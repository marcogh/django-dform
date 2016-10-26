# dform.fields.py
import logging
from six import with_metaclass

from django.core.exceptions import ValidationError
from django.forms import fields
from django.forms import widgets

logger = logging.getLogger(__name__)

FIELDS = []

# ============================================================================

class MetaField(type):
    def __new__(cls, name, bases, classdict):
        global FIELDS
        klass = type.__new__(cls, name, bases, dict(classdict))
        if klass.__name__ not in ['Field', 'ChoiceField']:
            FIELDS.append(klass)
        return klass


class Field(with_metaclass(MetaField)):
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


class IntegerStorage(object):
    storage_key = 'answer_int'

    @classmethod
    def check_value(cls, field_parms, value):
        try:
            int(value)
        except ValueError:
            raise ValidationError('value was not an integer')


class FloatStorage(object):
    storage_key = 'answer_float'

    @classmethod
    def check_value(cls, field_parms, value):
        try:
            float(value)
        except ValueError:
            raise ValidationError('value was not a float')

# ============================================================================
# Field Types
# ============================================================================

class Text(Field, TextStorage):
    field_key = 'tx'
    django_field = fields.CharField


class MultiText(Field, TextStorage):
    field_key = 'mt'
    django_field = fields.CharField
    django_widget = widgets.Textarea


class Email(Field, TextStorage):
    field_key = 'em'
    django_field = fields.EmailField


class Dropdown(ChoiceField, ChoicesStorage):
    field_key = 'dr'
    django_field = fields.ChoiceField
    django_widget = widgets.Select


class Radio(ChoiceField, ChoicesStorage):
    field_key = 'rd'
    django_field = fields.ChoiceField
    django_widget = widgets.RadioSelect
    form_control = False


class Checkboxes(ChoiceField, MultipleChoicesStorage):
    field_key = 'ch'
    django_field = fields.MultipleChoiceField
    django_widget = widgets.CheckboxSelectMultiple
    form_control = False


class Rating(Field, IntegerStorage):
    field_key = 'rt'
    django_field = fields.ChoiceField
    django_widget = widgets.RadioSelect


class Integer(Field, IntegerStorage):
    field_key = 'in'
    django_field = fields.IntegerField


class Float(Field, FloatStorage):
    field_key = 'fl'
    django_field = fields.FloatField

# ============================================================================

FIELDS_DICT = {f.field_key:f for f in FIELDS}
FIELD_CHOICES = [(f.field_key, f.__name__) for f in FIELDS]
FIELD_CHOICES_DICT = dict(FIELD_CHOICES)
