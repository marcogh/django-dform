import json, copy
from collections import OrderedDict
from django.core.exceptions import ValidationError
from django.test import TestCase

from awl.waelsteng import AdminToolsMixin
from wrench.utils import parse_link

from dform.admin import (SurveyAdmin, SurveyVersionAdmin, QuestionAdmin,
    QuestionOrderAdmin, AnswerAdmin)
from dform.models import (Survey, SurveyVersion, EditNotAllowedException, 
    Question, QuestionOrder, Answer)
from dform.fields import Text, MultiText, Dropdown, Radio, Checkboxes, Rating

# ============================================================================

#def pprint(data):
#    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))

def sample_survey():
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

# ============================================================================
# Test Objects
# ============================================================================

class SurveyTests(TestCase):
    def test_survey(self):
        survey, mt, tx, dr, rd, cb, rt = sample_survey()

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

        # -- check version is_editable
        self.assertTrue(first_version.is_editable())

        # -- test answers
        answer = 'answer and stuff and things'
        a1 = survey.answer_question(tx, 1, answer, first_version)
        self.assertEqual(a1.value, answer)

        # re-check version is_editable now that it shouldn't be
        self.assertFalse(first_version.is_editable())

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
        str(survey)
        str(first_version)
        str(tx)
        str(QuestionOrder.objects.first())
        str(a1)


    def test_survey_dicts(self):
        self.maxDiff = None
        survey, mt, tx, dr, rd, cb, rt = sample_survey()

        # -- create a delta that changes nothing
        expected = survey.to_dict()
        survey.replace_from_dict(expected)

        # verify that everything in the survey is the same, nothing new
        # created and the questions are in order
        self.assertEqual(1, Survey.objects.count())
        self.assertEqual(6, Question.objects.count())

        delta = survey.to_dict()
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
        survey.replace_from_dict(expected, survey.latest_version)

        expected['questions'][0]['id'] = Question.objects.last().id

        delta = survey.to_dict()
        self.assertEqual(expected, delta)

        # -- verify remove works
        delta = {
            'remove':[expected['questions'][0]['id'], ]
        }
        survey.replace_from_dict(delta)

        expected['questions'] = expected['questions'][1:]
        delta = survey.to_dict()
        self.assertEqual(expected, delta)

        # -- verify error conditions for bad question ids
        last_question = Question.objects.all().order_by('id').last()
        delta = {
            'questions':[{
                'id':last_question.id + 10,
            }]
        }

        with self.assertRaises(Question.DoesNotExist):
            survey.replace_from_dict(delta)

        # try remove
        delta = {
            'remove':[last_question.id + 10, ],
        }

        with self.assertRaises(Question.DoesNotExist):
            survey.replace_from_dict(delta)

        # -- verify disallowed editing
        survey.answer_question(mt, 1, 'answer\nanswer')

        with self.assertRaises(EditNotAllowedException):
            survey.replace_from_dict(delta)


class AdminTestCase(TestCase, AdminToolsMixin):
    def test_survey_admin(self):
        self.initiate()

        survey_admin = SurveyAdmin(Survey, self.site)
        version_admin = SurveyVersionAdmin(SurveyVersion, self.site)
        survey, _, tx, _, _, _, _ = sample_survey()
        first_version = survey.latest_version

        # check version number
        result = self.field_value(survey_admin, survey, 'version_num')
        self.assertEqual('1', result)

        # -- show_actions
        response = self.visit_admin_link(survey_admin, survey, 'show_actions')
        self.assertTemplateUsed(response, 'edit_survey.html')

        # verify SurveyVersion "edit" link
        response = self.visit_admin_link(version_admin, first_version, 
            'show_actions')
        self.assertTemplateUsed(response, 'edit_survey.html')

        # add answer and verify "new version" link
        answer = 'answer and stuff and things'
        survey.answer_question(tx, 1, answer)

        self.visit_admin_link(survey_admin, survey, 'show_actions',
            response_code=302)
        self.assertEqual(2, survey.latest_version.version_num)
        self.assertNotEqual(first_version, survey.latest_version)

        result = self.field_value(version_admin, first_version, 'show_actions')
        self.assertEqual('', result)

        # -- show_versions
        self.visit_admin_link(survey_admin, survey, 'show_versions')

    def _assert_question_fields(self, html, q_url, q_text, r_url):
        q_link, r_link = html.split('|')

        url, text = parse_link(q_link)
        self.assertIn(q_url, url)
        self.assertIn(q_text, text)

        url, text = parse_link(r_link)
        self.assertIn(r_url, url)
        self.assertIn('Reorder', text)

    def _assert_link(self, html, url, text):
        u, t = parse_link(html)
        self.assertIn(url, u)
        self.assertIn(text, t)

    def test_survey_admin_links(self):
        # different test cases from test_survey_admin that need non-standard
        # surveys to be built while we're testing, so this is going in its own
        # method
        self.initiate()

        survey_admin = SurveyAdmin(Survey, self.site)
        version_admin = SurveyVersionAdmin(SurveyVersion, self.site)
        survey = Survey.objects.create(name='survey')
        first_version = survey.latest_version

        # -- show_questions
        html = self.field_value(survey_admin, survey, 'show_questions')
        self.assertEqual('', html)

        html = self.field_value(version_admin, first_version, 'show_questions')
        self.assertEqual('', html)

        # add question, try again
        q_url = '/admin/dform/question/?survey_versions__id=%s' % (
            survey.latest_version.id)
        r_url = '/admin/dform/questionorder/?survey_version__id=%s' % (
            survey.latest_version.id)

        q = survey.add_question(Text, 'first question')

        html = self.field_value(survey_admin, survey, 'show_questions')
        self._assert_question_fields(html, q_url, '1 Question', r_url)
        self.assertNotIn('Questions', html)

        html = self.field_value(version_admin, first_version, 'show_questions')
        self._assert_question_fields(html, q_url, '1 Question', r_url)
        self.assertNotIn('Questions', html)

        # add question, handling multiples
        survey.add_question(Text, 'second question')

        html = self.field_value(survey_admin, survey, 'show_questions')
        self._assert_question_fields(html, q_url, '2 Questions', r_url)

        html = self.field_value(version_admin, first_version, 'show_questions')
        self._assert_question_fields(html, q_url, '2 Questions', r_url)

        # -- show answers
        url = '/admin/dform/answer/?survey_version__id=%s' % (
            survey.latest_version.id)

        # add answer
        survey.answer_question(q, 1, '1st Answer', first_version)

        html = self.field_value(survey_admin, survey, 'show_answers')
        self._assert_link(html, url, '1 Answer')
        self.assertNotIn('Answers', html)

        html = self.field_value(version_admin, first_version, 'show_answers')
        self._assert_link(html, url, '1 Answer')
        self.assertNotIn('Answers', html)

        # add another answer, handling multiples
        survey.answer_question(q, 2, '2nd Answer', first_version)

        html = self.field_value(survey_admin, survey, 'show_answers')
        self._assert_link(html, url, '2 Answers')

        html = self.field_value(version_admin, first_version, 'show_answers')
        self._assert_link(html, url, '2 Answers')

    def test_question_admin(self):
        self.initiate()

        question_admin = QuestionAdmin(Question, self.site)
        survey = Survey.objects.create(name='survey')
        version = survey.latest_version

        q1 = survey.add_question(Text, '1st question')
        q2 = survey.add_question(Text, '2nd question')

        # -- show_reorder
        url = '/admin/dform/questionorder/?survey_version__id=%s' % version.id
        html = self.field_value(question_admin, q1, 'show_reorder')
        self._assert_link(html, url, 'Reorder')

        # -- show_answers
        url = '/admin/dform/answer/?question__id=%s' % q1.id

        html = self.field_value(question_admin, q1, 'show_answers')
        self.assertEqual('', html)

        # add an answer
        a1 = survey.answer_question(q1, 1, '1st Answer', version)
        html = self.field_value(question_admin, q1, 'show_answers')
        self._assert_link(html, url, '1 Answer')
        self.assertNotIn('Answers', html)

        # another answer
        survey.answer_question(q1, 2, '2nd Answer', version)
        html = self.field_value(question_admin, q1, 'show_answers')
        self._assert_link(html, url, '2 Answers')

        # -- question order
        qo_admin = QuestionOrderAdmin(QuestionOrder, self.site)
        qo2 = QuestionOrder.objects.last()
        text = self.field_value(qo_admin, qo2, 'show_text')
        self.assertEqual('2nd question', text)

        # move_up & move_down tested in awl.rankedmodel, just trip them for
        # coverage
        self.field_value(qo_admin, qo2, 'move_up')
        self.field_value(qo_admin, qo2, 'move_down')

        # -- answer admin
        answer_admin = AnswerAdmin(Answer, self.site)
        text = self.field_value(answer_admin, a1, 'show_text')
        self.assertEqual('1st question', text)

        text = self.field_value(answer_admin, a1, 'show_field_key')
        self.assertEqual('Text', text)

# ============================================================================
# Test Views
# ============================================================================

class SurveyViewTests(TestCase, AdminToolsMixin):
    def test_survey_delta_view(self):
        self.maxDiff = None
        survey, mt, tx, dr, rd, cb, rt = sample_survey()

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

        response = self.client.post('/dform/survey_delta/0/',
            data={'delta':json.dumps(expected)})
        self.assertEqual(200, response.status_code)

        expected['questions'][0]['id'] = Question.objects.last().id

        survey2 = Survey.objects.last()
        delta = survey2.to_dict()
        self.assertEqual(expected, delta)

        self.assertEqual(2, Survey.objects.count())
        self.assertEqual(7, Question.objects.count())

        # -- verify mismatched question/survey is refused
        delta = {
            'questions':[{
                'id':mt.id,   # question from survey1
            }]
        }

        response = self.client.post(
            '/dform/survey_delta/%s/' % survey2.latest_version.id, 
            data={'delta':json.dumps(delta)})

        self.assertEqual(404, response.status_code)

        # -- verify error conditions for bad question ids
        last_question = Question.objects.all().order_by('id').last()
        delta = {
            'questions':[{
                'id':last_question.id + 10,
            }]
        }

        response = self.client.post(
            '/dform/survey_delta/%s/' % survey.latest_version.id, 
            data={'delta':json.dumps(delta)})

        self.assertEqual(404, response.status_code)

        # try remove
        delta = {
            'remove':[last_question.id + 10, ],
        }

        response = self.client.post(
            '/dform/survey_delta/%s/' % survey.latest_version.id, 
            data={'delta':json.dumps(delta)})

        self.assertEqual(404, response.status_code)

        # -- verify disallowed editing
        survey.answer_question(mt, 1, 'answer\nanswer')
        delta = {
            'name':'Foo',
        }

        response = self.client.post(
            '/dform/survey_delta/%s/' % survey.latest_version.id, 
            data={'delta':json.dumps(delta)})

        self.assertEqual(404, response.status_code)

    def test_survey_edit(self):
        # Only does rudimentary execution tests, doesn't test the actual 
        # javascript editor
        self.initiate()

        response = self.authed_get('/dform/survey_editor/0/')
        self.assertTemplateUsed(response, 'edit_survey.html')

        survey = Survey.objects.first()

        response = self.authed_get('/dform/survey_editor/%s/' %
            survey.latest_version.id)
        self.assertTemplateUsed(response, 'edit_survey.html')