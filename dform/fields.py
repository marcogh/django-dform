# dform.fields.py
import logging

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# ============================================================================

class Field(object):
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


class MultiText(Field, TextStorage):
    field_key = 'mt'


class Dropdown(ChoiceField, ChoicesStorage):
    field_key = 'dr'


class Radio(ChoiceField, ChoicesStorage):
    field_key = 'rd'


class Checkboxes(ChoiceField, ChoicesStorage):
    field_key = 'ch'


class Rating(Field, NumberStorage):
    field_key = 'rt'

# ============================================================================

FIELDS = [Text, MultiText, Dropdown, Radio, Checkboxes, Rating]
FIELDS_DICT = {f.field_key:f for f in FIELDS}
FIELD_CHOICES = [(f.field_key, f.__name__) for f in FIELDS]
FIELD_CHOICES_DICT = dict(FIELD_CHOICES)