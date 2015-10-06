# create_test_data.py
from django.core.management.base import BaseCommand

from dform.models import Survey
from dform.fields import Text, MultiText, Dropdown, Radio, Checkboxes, Rating

# =============================================================================

colours = [ 'Pink', 'LightPink', 'HotPink', 'DeepPink', 'PaleVioletRed', 
    'MediumVioletRed', 'LightSalmon', 'Salmon', 'DarkSalmon', 'LightCoral',
    'IndianRed', 'Crimson', 'FireBrick', 'DarkRed', 'Red', 'OrangeRed',
    'Tomato', 'Coral', 'DarkOrange', 'Orange', 'Yellow', 'LightYellow',
    'LemonChiffon', 'LightGoldenrodYellow', 'PapayaWhip', 'Moccasin',
    'PeachPuff', 'PaleGoldenrod', 'Khaki', 'DarkKhaki', 'Gold', 'Cornsilk',
    'BlanchedAlmond', 'Bisque', 'NavajoWhite', 'Wheat', 'BurlyWood', 'Tan',
    'RosyBrown', 'SandyBrown', 'Goldenrod', 'DarkGoldenrod', 'Peru',
    'Chocolate', 'SaddleBrown', 'Sienna', 'Brown', 'Maroon', 'DarkOliveGreen',
    'Olive', 'OliveDrab', 'YellowGreen', 'LimeGreen', 'Lime', 'LawnGreen',
    'Chartreuse', 'GreenYellow', 'SpringGreen', 'MediumSpringGreen',
    'LightGreen', 'PaleGreen', 'DarkSeaGreen', 'MediumSeaGreen', 'SeaGreen',
    'ForestGreen', 'Green', 'DarkGreen', 'MediumAquamarine', 'Aqua', 'Cyan',
    'LightCyan', 'PaleTurquoise', 'Aquamarine', 'Turquoise',
    'MediumTurquoise', 'DarkTurquoise', 'LightSeaGreen', 'CadetBlue',
    'DarkCyan', 'Teal', 'LightSteelBlue', 'PowderBlue', 'LightBlue',
    'SkyBlue', 'LightSkyBlue', 'DeepSkyBlue', 'DodgerBlue', 'CornflowerBlue',
    'SteelBlue', 'RoyalBlue', 'Blue', 'MediumBlue', 'DarkBlue', 'Navy',
    'MidnightBlue', 
]

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

        survey = Survey.objects.create(name='Favourites Survey')
        q = survey.add_question(Text, 'What is your favourite colour?')
        
        # generate some answers
        counter = 1
        for colour in colours:
            survey.answer_question(q, counter, colour)
            counter += 1

        survey.new_version()
        q2 = survey.add_question(Text, 
            'What is your favourite way of spelling "favourite"?')

        survey.answer_question(q, counter, colour[0])
        survey.answer_question(q2, counter, 'favourite')
        counter += 1

        survey.answer_question(q, counter, colour[1])
        survey.answer_question(q2, counter, 'with the "u"')
        counter += 1

        survey.new_version()
