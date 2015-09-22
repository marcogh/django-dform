from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Survey, EditNotAllowedException
from .fields import Text, MultiText, Dropdown, Radio, Checkboxes, Rating

# ============================================================================

#def pprint(data):
#    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))

# ============================================================================
# Test Class
# ============================================================================

class SurveyTests(TestCase):
    def test_survey(self):
        survey = Survey.objects.create(name='survey')

        # verify version created and correct value
        first_version = survey.latest_version
        self.assertEqual(first_version.version_num, 1)

        # add some questions
        mt = survey.add_question(MultiText, 'multi')
        tx = survey.add_question(Text, 'text value and stuff and things', 
            rank=1)
        dr = survey.add_question(Dropdown, 'drop', 
            field_parms={'a':'Apple', 'b':'Bear'})
        rd = survey.add_question(Radio, 'radio', 
            field_parms={'c':'Chair', 'd':'Dog'})
        cb = survey.add_question(Checkboxes, 'check', 
            field_parms={'e':'Egg', 'f':'Fan'})
        rt = survey.add_question(Rating, 'rating')

        # verify order works
        expected_q1 = [tx, mt, dr, rd, cb, rt]
        for index, question in enumerate(survey.questions()):
            self.assertEqual(question, expected_q1[index])

        # -- check validation on fields
        with self.assertRaises(ValidationError):
            survey.add_question(Text, 'text', field_parms={'a':'a'})
        with self.assertRaises(ValidationError):
            survey.add_question(Dropdown, 'text')
        with self.assertRaises(ValidationError):
            survey.add_question(Dropdown, 'text', field_parms=[])

        # -- spawn a new version
        second_version = survey.new_version()
        self.assertEqual(second_version.version_num, 2)
        self.assertEqual(second_version, survey.latest_version)

        # verify order on new version
        for index, question in enumerate(survey.questions()):
            self.assertEqual(question, expected_q1[index])

        # change second version
        survey.remove_question(rt)
        tx2 = survey.add_question(Text, 'text 2')

        # verify old and new versions are still have correct questions
        for index, question in enumerate(survey.questions(first_version)):
            self.assertEqual(question, expected_q1[index])

        expected_q2 = [tx, mt, dr, rd, cb, tx2]
        for index, question in enumerate(survey.questions()):
            self.assertEqual(question, expected_q2[index])

        # -- test answers
        answer = 'answer and stuff and things'
        a1 = survey.answer_question(tx, 1, answer, first_version)
        self.assertEqual(a1.value, answer)

        # survey has answers now, shouldn't be able to edit
        with self.assertRaises(EditNotAllowedException):
            survey.add_question(Text, 'fail', version=first_version)

        with self.assertRaises(EditNotAllowedException):
            survey.remove_question(tx, version=first_version)

        # more answers
        a = survey.answer_question(mt, 1, 'answer\nanswer', first_version)
        self.assertEqual(a.value, 'answer\nanswer')

        a = survey.answer_question(dr, 1, 'a', first_version)
        self.assertEqual(a.value, 'a')
        with self.assertRaises(ValidationError):
            survey.answer_question(dr, 1, 'z', first_version)

        a = survey.answer_question(rd, 1, 'c', first_version)
        self.assertEqual(a.value, 'c')
        with self.assertRaises(ValidationError):
            survey.answer_question(dr, 1, 'z', first_version)

        a = survey.answer_question(cb, 1, 'e', first_version)
        self.assertEqual(a.value, 'e')
        with self.assertRaises(ValidationError):
            survey.answer_question(dr, 'z', first_version)

        a = survey.answer_question(rt, 1, 1, first_version)
        self.assertEqual(a.value, 1.0)

        # check number validation
        with self.assertRaises(ValidationError):
            survey.answer_question(rt, 1, 'a', first_version)

        # try to answer a question not in this version
        with self.assertRaises(AttributeError):
            survey.answer_question(rt, 1, 1, second_version)

        # -- misc coverage items
        str(tx)
        str(a1)
