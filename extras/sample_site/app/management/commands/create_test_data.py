# create_test_data.py

from django.core.management.base import BaseCommand

from dform.models import Survey
from dform.fields import Text, MultiText, Dropdown, Radio, Checkboxes, Rating

# =============================================================================

class Command(BaseCommand):
    def handle(self, *args, **options):
        survey = Survey.objects.create(name='Sample Survey')
        survey.add_question(MultiText, 'Multitext question')
        survey.add_question(Text, 'Single line text question')
        survey.add_question(Dropdown, 'Favourite a fruit', 
            field_parms={'a':'Apple', 'b':'Banana', 'k':'Kiwi'})
        survey.add_question(Checkboxes, 'Choose all that apply',
            field_parms={'b':'BMW', 'v':'Volkswagon', 'a':'Audi'})
        survey.add_question(Rating, 'Rate our service')
