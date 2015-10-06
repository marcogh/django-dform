import json, copy
from collections import OrderedDict
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Survey, EditNotAllowedException, Question
from .fields import Text, MultiText, Dropdown, Radio, Checkboxes, Rating

# ============================================================================

#def pprint(data):
#    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))

# ============================================================================
# Test Class
# ============================================================================

class SurveyTests(TestCase):
    def _base_survey(self):
        # Creates and returns a survey and its questions
        survey = Survey.objects.create(name='survey')

        # add some questions
        mt = survey.add_question(MultiText, 'multi')
        tx = survey.add_question(Text, 'text value and stuff and things')
        o = OrderedDict([('a', 'Apple'), ('b', 'Bear')])
        dr = survey.add_question(Dropdown, 'drop', field_parms=o)
        o = OrderedDict([('c', 'Chair'), ('d','Dog')])
        rd = survey.add_question(Radio, 'radio', field_parms=o)
        o = OrderedDict([('e', 'Egg'), ('f', 'Fan')])
        cb = survey.add_question(Checkboxes, 'check', field_parms=o) 
        rt = survey.add_question(Rating, 'rating')

        return survey, mt, tx, dr, rd, cb, rt

    def test_survey(self):
        survey, mt, tx, dr, rd, cb, rt = self._base_survey()

        # verify version created and correct value
        first_version = survey.latest_version
        self.assertEqual(first_version.version_num, 1)

        # verify order works
        expected_q1 = [mt, tx, dr, rd, cb, rt]
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
        tx2 = survey.add_question(Text, 'text 2', rank=1)

        # verify old and new versions are still have correct questions
        for index, question in enumerate(survey.questions(first_version)):
            self.assertEqual(question, expected_q1[index])

        expected_q2 = [tx2, mt, tx, dr, rd, cb]
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

    def _create_delta(self, version):
        questions = []
        for question in version.survey.questions(version):
            questions.append({
                'id':question.id,
                'field_key':question.field_key,
                'text':question.text,
                'required':question.required,
                'field_parms':question.field_parms,
            })

        delta = {
            'name':version.survey.name,
            'questions':questions,
        }

        return delta

    def test_survey_delta_view(self):
        self.maxDiff = None
        survey, mt, tx, dr, rd, cb, rt = self._base_survey()

        # -- create a delta that changes nothing
        expected = self._create_delta(survey.latest_version)

        response = self.client.post(
            '/survey_delta/%s/' % survey.latest_version.id,
            data={'delta':json.dumps(expected)})
        self.assertEqual(200, response.status_code)

        # verify that everything in the survey is the same, nothing new
        # created and the questions are in order
        self.assertEqual(1, Survey.objects.count())
        self.assertEqual(6, Question.objects.count())

        delta = self._create_delta(survey.latest_version)
        self.assertEqual(expected, delta)

        # -- rename survey, change questions: reorder, edit and add
        expected['name'] = 'Renamed'
        expected['questions'][4], expected['questions'][5] = \
            expected['questions'][5], expected['questions'][4]
        expected['questions'][0].update({
            'text':'edit text label',
            'required':True,
        })
        expected['questions'].insert(0, {
            'id':0,
            'field_key':Dropdown.field_key,
            'text':'a new question',
            'required':True,
            'field_parms':OrderedDict([('g', 'Good'), ('h', 'Hello')])
        })

        # perform delta, change id of new question in "expected"
        response = self.client.post(
            '/survey_delta/%s/' % survey.latest_version.id,
            data={'delta':json.dumps(expected)})
        self.assertEqual(200, response.status_code)

        expected['questions'][0]['id'] = Question.objects.last().id

        delta = self._create_delta(survey.latest_version)
        self.assertEqual(expected, delta)

        # -- verify remove works
        delta = {
            'remove':[expected['questions'][0]['id'], ]
        }
        response = self.client.post(
            '/survey_delta/%s/' % survey.latest_version.id,
            data={'delta':json.dumps(delta)})
        self.assertEqual(200, response.status_code)

        expected['questions'] = expected['questions'][1:]
        delta = self._create_delta(survey.latest_version)
        self.assertEqual(expected, delta)

        # -- create a new survey
        expected = {
            'name':'New Survey',
            'questions':[{
                'id':0,
                'field_key':Dropdown.field_key,
                'text':'a new question',
                'required':True,
                'field_parms':OrderedDict([('g', 'Good'), ('h', 'Hello')])
            }],
        }

        response = self.client.post('/survey_delta/0/',
            data={'delta':json.dumps(expected)})
        self.assertEqual(200, response.status_code)

        expected['questions'][0]['id'] = Question.objects.last().id

        survey2 = Survey.objects.last()
        delta = self._create_delta(survey2.latest_version)
        self.assertEqual(expected, delta)

        self.assertEqual(2, Survey.objects.count())
        self.assertEqual(8, Question.objects.count())

        # -- verify disallowed editing
        survey.answer_question(mt, 1, 'answer\nanswer')
        response = self.client.post(
            '/survey_delta/%s/' % survey.latest_version.id, data={'delta':'{}'})
        self.assertEqual(404, response.status_code)

        # -- verify mismatched question/survey is refused
        delta = {
            'questions':[{
                'id':mt.id,   # question from survey1
            }]
        }

        response = self.client.post(
            '/survey_delta/%s/' % survey2.latest_version.id, 
            data={'delta':json.dumps(delta)})

        self.assertEqual(404, response.status_code)
