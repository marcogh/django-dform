import json, re
from collections import OrderedDict
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse, NoReverseMatch
from django.test import TestCase
from mock import patch

from awl.utils import refetch
from awl.waelsteng import AdminToolsMixin
from wrench.utils import parse_link

from dform.admin import (SurveyAdmin, SurveyVersionAdmin, QuestionAdmin,
    QuestionOrderAdmin, AnswerAdmin, AnswerGroupAdmin)
from dform.models import (Survey, SurveyVersion, EditNotAllowedException, 
    Question, QuestionOrder, Answer, AnswerGroup)
from dform.fields import (Text, MultiText, Dropdown, Radio, Checkboxes,
    Rating, Integer, Float)
from dform.forms import SurveyForm

# ============================================================================

#def pprint(data):
#    print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))

RE_PYM = re.compile('pym\.js')

class GotHere(Exception):
    pass


def perm_hook(name, *args, **kwargs):
    raise GotHere()


def create_survey():
    # Creates and returns a survey and its questions
    survey = Survey.factory(name='survey')

    # add some questions
    fields = OrderedDict()
    fields['multitext'] = survey.add_question(MultiText, 'multi')
    fields['text'] = survey.add_question(Text, 
        'text value and stuff and things')
    o = OrderedDict([('a', 'Apple'), ('b', 'Bear')])
    fields['dropdown'] = survey.add_question(Dropdown, 'drop', 
        field_parms=o)
    o = OrderedDict([('c', 'Chair'), ('d','Dog')])
    fields['radio'] = survey.add_question(Radio, 'radio', field_parms=o)
    o = OrderedDict([('e', 'Egg'), ('f', 'Fan')])
    fields['checkboxes'] = survey.add_question(Checkboxes, 'check', 
        field_parms=o) 
    fields['rating'] = survey.add_question(Rating, 'rating')
    fields['integer'] = survey.add_question(Integer, 'integer')
    fields['float'] = survey.add_question(Float, 'float')

    return survey, fields

# ============================================================================
# Test Objects
# ============================================================================

class SurveyTests(TestCase):
    def test_survey(self):
        survey, fields = create_survey()

        # verify version created and correct value
        first_version = survey.latest_version
        self.assertEqual(first_version.version_num, 1)

        # verify order works
        expected_q1 = list(fields.values())
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
        survey.remove_question(fields['rating'])
        text2 = survey.add_question(Text, 'text 2', rank=1)

        # verify old and new versions are still have correct questions
        for index, question in enumerate(first_version.questions()):
            self.assertEqual(question, expected_q1[index])

        # new expectation has text2 inserted at front and no ratings
        expected_q2 = [text2, ] + list(fields.values())
        del expected_q2[6]  # rating element

        for index, question in enumerate(survey.questions()):
            self.assertEqual(question, expected_q2[index])

        # -- check version is_editable
        self.assertTrue(first_version.is_editable())

        # -- test answers
        answer = 'answer and stuff and things'
        answer_group = AnswerGroup.factory(survey_version=first_version)
        a1 = first_version.answer_question(fields['text'], answer_group, answer)
        self.assertEqual(a1.value, answer)

        # answer same question again, ensure replacement
        a2 = first_version.answer_question(fields['text'], answer_group, 
            'something else')
        self.assertEqual(a1.id, a2.id)
        self.assertEqual(a2.value, 'something else')

        # re-check version is_editable now that it shouldn't be
        self.assertFalse(first_version.is_editable())

        # survey has answers now, shouldn't be able to edit
        with self.assertRaises(EditNotAllowedException):
            first_version.add_question(Text, 'fail')

        with self.assertRaises(EditNotAllowedException):
            first_version.remove_question(fields['text'])

        # more answers
        a = first_version.answer_question(fields['multitext'], answer_group, 
            'answer\nanswer')
        self.assertEqual(a.value, 'answer\nanswer')

        a = first_version.answer_question(fields['dropdown'], answer_group, 'a')
        self.assertEqual(a.value, 'a')
        with self.assertRaises(ValidationError):
            first_version.answer_question(fields['dropdown'], answer_group, 'z')

        a = first_version.answer_question(fields['radio'], answer_group, 'c')
        self.assertEqual(a.value, 'c')
        with self.assertRaises(ValidationError):
            first_version.answer_question(fields['dropdown'], answer_group, 'z')

        a = first_version.answer_question(fields['checkboxes'], answer_group, 
            'e')
        self.assertEqual(a.value, 'e')

        a = first_version.answer_question(fields['integer'], answer_group, 1)
        self.assertEqual(a.value, 1)
        with self.assertRaises(ValidationError):
            first_version.answer_question(fields['integer'], answer_group, 'z')

        a = first_version.answer_question(fields['float'], answer_group, 1.2)
        self.assertEqual(a.value, 1.2)
        with self.assertRaises(ValidationError):
            first_version.answer_question(fields['float'], answer_group, 'z')

        # create some more answer groups, do some data association as well
        # (doesn't matter with what, so we'll associate it with another AG)
        ag2 = AnswerGroup.factory(first_version, answer_group)
        ag3 = AnswerGroup.factory(first_version)
        a = first_version.answer_question(fields['checkboxes'], ag2, 'e,f')
        self.assertEqual(a.value, 'e,f')
        with self.assertRaises(ValidationError):
            first_version.answer_question(fields['checkboxes'], ag3, 'z')
        with self.assertRaises(ValidationError):
            first_version.answer_question(fields['checkboxes'], ag3, 'e,z')

        a = first_version.answer_question(fields['rating'], answer_group, 1)
        self.assertEqual(a.value, 1)

        # check number validation
        with self.assertRaises(ValidationError):
            first_version.answer_question(fields['rating'], answer_group, 'a')

        # try to answer a question not in this version
        with self.assertRaises(AttributeError):
            survey.answer_question(fields['rating'], answer_group, 1)

        # -- misc coverage items
        str(survey)
        str(first_version)
        str(fields['text'])
        str(QuestionOrder.objects.first())
        str(answer_group)
        str(a1)


    def test_survey_dicts(self):
        self.maxDiff = None
        survey, fields = create_survey()

        # -- create a delta that changes nothing
        expected = survey.to_dict()
        survey.replace_from_dict(expected)

        # verify that everything in the survey is the same, nothing new
        # created and the questions are in order
        self.assertEqual(1, Survey.objects.count())
        self.assertEqual(8, Question.objects.count())

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
        survey.replace_from_dict(expected)

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
        ag = AnswerGroup.factory(survey_version=survey.latest_version)
        survey.answer_question(fields['multitext'], ag, 'answer\nanswer')

        with self.assertRaises(EditNotAllowedException):
            survey.replace_from_dict(delta)

    def test_on_success(self):
        survey = Survey.factory(name='test')
        version = survey.latest_version

        with self.assertRaises(AttributeError):
            version.on_success()

        with self.settings(DFORM_SUCCESS_REDIRECT='/one/'):
            self.assertEqual('/one/', version.on_success())

            survey.success_redirect = '/two/'
            survey.save()
            survey = refetch(survey)
            version = refetch(version)
            self.assertEqual('/two/', version.on_success())

            version.success_redirect = '/three/'
            self.assertEqual('/three/', version.on_success())


def fake_reverse(name, args):
    if name in ['dform-sample-survey', 'dform-survey',
            'dform-embedded-survey', 'dform-survey-with-answers',
            'dform-embedded-survey-with-answers']:
        raise NoReverseMatch

    return reverse(name, args=args)


class AdminTestCase(TestCase, AdminToolsMixin):
    def test_without_urls(self):
        # what actions are available depend on whether the dform.urls.py file
        # is used or not, and need to be able to change if it isn't there; it
        # is always there when testing, so we'll need to use mock to force the
        # code to execute
        self.initiate()
        survey_admin = SurveyAdmin(Survey, self.site)
        version_admin = SurveyVersionAdmin(SurveyVersion, self.site)
        group_admin = AnswerGroupAdmin(AnswerGroup, self.site)
        survey, fields = create_survey()

        with patch('dform.admin.reverse') as mock_reverse:
            mock_reverse.side_effect = fake_reverse

            html = self.field_value(survey_admin, survey, 'show_actions')
            actions = html.split(',')
            self.assertEqual(2, len(actions))

            url, text = parse_link(actions[0])
            self.assertEqual(text, 'Edit Survey')

            url, text = parse_link(actions[1])
            self.assertEqual(text, 'Show Links')

            # -- SurveyVersion of same test
            result = self.field_value(version_admin, survey.latest_version, 
                'show_actions')
            self.assertEqual(2, len(actions))

            url, text = parse_link(actions[0])
            self.assertEqual(text, 'Edit Survey')

            url, text = parse_link(actions[1])
            self.assertEqual(text, 'Show Links')

            # -- repeat with locked survey
            answer = 'answer and stuff and things'
            ag = AnswerGroup.factory(survey_version=survey.latest_version)
            survey.answer_question(fields['text'], ag, answer)

            html = self.field_value(survey_admin, survey, 'show_actions')
            actions = html.split(',')
            self.assertEqual(2, len(actions))

            url, text = parse_link(actions[0])
            self.assertEqual(text, 'New Version')

            url, text = parse_link(actions[1])
            self.assertEqual(text, 'Show Links')

            # -- SurveyVersion of same test
            html = self.field_value(version_admin, survey.latest_version, 
                'show_actions')
            actions = html.split(',')
            self.assertEqual(1, len(actions))

            url, text = parse_link(actions[0])
            self.assertEqual(text, 'Show Links')

            # -- check actions on AG
            result = self.field_value(group_admin, ag, 'show_actions')
            self.assertEqual('', result)

    def assert_edit_link(self, link):
        url, text = parse_link(link)
        self.assertEqual('Edit Survey', text)

        response = self.authed_get(url)
        self.assertTemplateUsed(response, 'dform/edit_survey.html')

    def assert_show_link(self, link):
        url, text = parse_link(link)
        self.assertEqual('Show Links', text)

        response = self.authed_get(url)
        self.assertTemplateUsed(response, 'dform/links_survey.html')

    def assert_sample_link(self, link):
        url, text = parse_link(link)
        self.assertEqual('View Sample', text)

        response = self.authed_get(url)
        self.assertTemplateUsed(response, 'dform/survey.html')

    def assert_change_link(self, link):
        url, text = parse_link(link)
        self.assertEqual('Answer Survey', text)

        response = self.authed_get(url)
        self.assertTemplateUsed(response, 'dform/survey.html')

    def assert_version_link(self, link):
        url, text = parse_link(link)
        self.assertEqual('New Version', text)

        self.authed_get(url, response_code=302)

    def test_survey_admin(self):
        self.initiate()

        survey_admin = SurveyAdmin(Survey, self.site)
        version_admin = SurveyVersionAdmin(SurveyVersion, self.site)
        survey, fields = create_survey()
        first_version = survey.latest_version

        # check version number
        result = self.field_value(survey_admin, survey, 'version_num')
        self.assertEqual('1', result)

        # -- show_actions
        links = self.field_value(survey_admin, survey, 'show_actions')
        edit, show, sample, change = links.split(',')
        self.assert_edit_link(edit)
        self.assert_show_link(show)
        self.assert_sample_link(sample)
        self.assert_change_link(change)

        links = self.field_value(version_admin, first_version, 'show_actions')
        edit, show, sample, change = links.split(',')
        self.assert_edit_link(edit)
        self.assert_show_link(show)
        self.assert_sample_link(sample)
        self.assert_change_link(change)

        # add answer and verify "new version" link
        answer = 'answer and stuff and things'
        ag = AnswerGroup.factory(survey_version=survey.latest_version)
        survey.answer_question(fields['text'], ag, answer)

        links = self.field_value(survey_admin, survey, 'show_actions')
        version, show, sample, change = links.split(',')
        self.assert_version_link(version)
        self.assert_show_link(show)
        self.assert_sample_link(sample)
        self.assert_change_link(change)

        links = self.field_value(version_admin, first_version, 'show_actions')
        show, sample, change = links.split(',')
        self.assert_show_link(show)
        self.assert_sample_link(sample)
        self.assert_change_link(change)

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
        group_admin = AnswerGroupAdmin(AnswerGroup, self.site)
        survey = Survey.factory(name='survey')
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

        # verify "show answers" URLs no answers
        html = self.field_value(survey_admin, survey, 'show_answers')
        self.assertEqual('', html)

        html = self.field_value(version_admin, first_version, 'show_answers')
        self.assertEqual('', html)

        # add answer
        ag = AnswerGroup.factory(survey_version=survey.latest_version)
        survey.answer_question(q, ag, '1st Answer')

        # urls for these answers
        sa_url = '/admin/dform/answergroup/?survey_version__survey__id=%s' % (
            survey.latest_version.id)
        sva_url = '/admin/dform/answergroup/?survey_version__id=%s' % (
            survey.latest_version.id)
        ch_url = '/dform/survey_with_answers/%s/%s/%s/%s/' % (
            survey.latest_version.id, survey.token, ag.id, ag.token)
        link_url = '/dform_admin/answer_links/%s/' % survey.latest_version.id

        # verify AG "show actions" URLs
        html = self.field_value(group_admin, ag, 'show_actions')
        actions = html.split(',')
        self.assertEqual(2, len(actions))
        self._assert_link(actions[0], ch_url, 'Change Answers')
        self._assert_link(actions[1], link_url, 'Show Links')

        # verify "show answers" URLs, single answer
        html = self.field_value(survey_admin, survey, 'show_answers')
        self._assert_link(html, sa_url, '1 Answer Set')
        self.assertNotIn('Answers', html)

        html = self.field_value(version_admin, first_version, 'show_answers')
        self._assert_link(html, sva_url, '1 Answer Set')
        self.assertNotIn('Answers', html)

        # add another answer, handling multiples
        ag2 = AnswerGroup.factory(survey_version=survey.latest_version)
        survey.answer_question(q, ag2, '2nd Answer')

        html = self.field_value(survey_admin, survey, 'show_answers')
        self._assert_link(html, sa_url, '2 Answer Sets')

        html = self.field_value(version_admin, first_version, 'show_answers')
        self._assert_link(html, sva_url, '2 Answer Sets')

        # --- misc for coverage
        self.assertTrue(
            group_admin.lookup_allowed('survey_version__survey__id', 1))
        self.assertFalse(
            group_admin.lookup_allowed('survey_version__survey', 1))

    def test_question_admin(self):
        self.initiate()

        question_admin = QuestionAdmin(Question, self.site)
        survey = Survey.factory(name='survey')
        version = survey.latest_version

        q1 = survey.add_question(Text, '1st question')
        survey.add_question(Text, '2nd question')

        # -- show_reorder
        url = '/admin/dform/questionorder/?survey_version__id=%s' % version.id
        html = self.field_value(question_admin, q1, 'show_reorder')
        self._assert_link(html, url, 'Reorder')

        # -- show_answers
        url = '/admin/dform/answer/?question__id=%s' % q1.id

        html = self.field_value(question_admin, q1, 'show_answers')
        self.assertEqual('', html)

        # add an answer
        ag = AnswerGroup.factory(survey_version=survey.latest_version)
        a1 = survey.answer_question(q1, ag, '1st Answer')
        html = self.field_value(question_admin, q1, 'show_answers')
        self._assert_link(html, url, '1 Answer')
        self.assertNotIn('Answers', html)

        # another answer
        ag2 = AnswerGroup.factory(survey_version=survey.latest_version)
        survey.answer_question(q1, ag2, '2nd Answer')
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

    def test_answer(self):
        self.initiate()

        answer_group_admin = AnswerGroupAdmin(AnswerGroup, self.site)

        survey = Survey.factory(name='survey')
        q1 = survey.add_question(Text, '1st question')

        # create a basic AnswerGroup and test its results
        ag1 = AnswerGroup.factory(survey_version=survey.latest_version)

        result = self.field_value(answer_group_admin, ag1, 'show_data')
        self.assertEqual('', result)
        html = self.field_value(answer_group_admin, ag1, 'show_questions')
        url, text = parse_link(html)
        self.assertEqual('1 Question', text)
        result = self.field_value(answer_group_admin, ag1, 'show_answers')
        self.assertEqual('', result)

        # add a question and check for change
        q2 = survey.add_question(Text, '2nd question')

        html = self.field_value(answer_group_admin, ag1, 'show_questions')
        url, text = parse_link(html)
        self.assertEqual('2 Questions', text)

        # add an answer and check for change
        survey.answer_question(q1, ag1, 'stuff')
        html = self.field_value(answer_group_admin, ag1, 'show_answers')
        url, text = parse_link(html)
        self.assertEqual('1 Answer', text)

        # add another answer
        survey.answer_question(q2, ag1, 'stuff')
        html = self.field_value(answer_group_admin, ag1, 'show_answers')
        url, text = parse_link(html)
        self.assertEqual('2 Answers', text)


# ============================================================================
# Test Views
# ============================================================================

class SurveyAdminViewTests(TestCase, AdminToolsMixin):
    def test_survey_delta_view(self):
        self.initiate()
        self.maxDiff = None
        survey, fields = create_survey()

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

        self.authed_post('/dform_admin/survey_delta/0/',
            data={'delta':json.dumps(expected)})

        expected['questions'][0]['id'] = Question.objects.last().id

        survey2 = Survey.objects.last()
        delta = survey2.to_dict()
        self.assertEqual(expected, delta)

        self.assertEqual(2, Survey.objects.count())
        self.assertEqual(9, Question.objects.count())

        # -- verify mismatched question/survey is refused
        delta = {
            'questions':[{
                'id':fields['multitext'].id,   # question from survey1
            }]
        }

        self.authed_post('/dform_admin/survey_delta/%s/' % (
            survey2.latest_version.id), response_code=404, 
            data={'delta':json.dumps(delta)})

        # -- verify error conditions for bad question ids
        last_question = Question.objects.all().order_by('id').last()
        delta = {
            'questions':[{
                'id':last_question.id + 10,
            }]
        }

        self.authed_post('/dform_admin/survey_delta/%s/' % (
            survey.latest_version.id), response_code=404, 
            data={'delta':json.dumps(delta)})

        # try remove
        delta = {
            'remove':[last_question.id + 10, ],
        }

        self.authed_post('/dform_admin/survey_delta/%s/' % (
            survey.latest_version.id), response_code=404, 
            data={'delta':json.dumps(delta)})

        # -- verify disallowed editing
        ag = AnswerGroup.factory(survey_version=survey.latest_version)
        survey.answer_question(fields['multitext'], ag, 'answer\nanswer')
        delta = {
            'name':'Foo',
        }

        self.authed_post('/dform_admin/survey_delta/%s/' % (
            survey.latest_version.id), response_code=404, 
            data={'delta':json.dumps(delta)})

    def test_survey_edit(self):
        # Only does rudimentary execution tests, doesn't test the actual 
        # javascript editor
        self.initiate()

        response = self.authed_get('/dform_admin/survey_editor/0/')
        self.assertTemplateUsed(response, 'dform/edit_survey.html')

        survey = Survey.objects.first()

        response = self.authed_get('/dform_admin/survey_editor/%s/' %
            survey.latest_version.id)
        self.assertTemplateUsed(response, 'dform/edit_survey.html')

    def test_show_links(self):
        self.initiate()
        survey, fields = create_survey()

        # test survey links page
        response = self.authed_get('/dform_admin/survey_links/%s/' % (
            survey.latest_version.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual('Links for: survey', response.context['title'])
        self.assertTemplateUsed(response, 'dform/links_survey.html')

        # test survey with answer links page
        ag = AnswerGroup.factory(survey_version=survey.latest_version)
        survey.answer_question(fields['multitext'], ag, 'an answer')

        response = self.authed_get('/dform_admin/answer_links/%s/' % ag.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual('Answer Links for: survey', response.context['title'])
        self.assertTemplateUsed(response, 'dform/links_answers.html')


class SurveyViewTests(TestCase):
    def _data_gen(self):
        redirect = '/admin/'
        survey, fields = create_survey()
        survey.success_redirect = redirect
        survey.save()

        return survey, fields

    def test_sample_survey(self):
        survey, fields = create_survey()

        response = self.client.get('/dform/sample_survey/%s/' % (
            survey.latest_version.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual('Sample: survey', response.context['title'])
        self.assertTemplateUsed(response, 'dform/survey.html')

    #---- Survey Views
    def _survey_view(self, url_base, expect_pym):
        survey, fields = self._data_gen()
        expected = list(zip(fields.values(), ['mt', 'tx', 'a', 'c', 'e', 2, 42, 
            13.69]))
        url = url_base % (survey.latest_version.id, survey.token)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual('survey', response.context['title'])
        self.assertTemplateUsed(response, 'dform/survey.html')

        # verify pym.js is included or absent as expected
        found_pym = RE_PYM.search(response.content.decode('utf-8'))
        if expect_pym:
            self.assertEqual(None, found_pym)
        else:
            self.assertFalse(found_pym)
        
        data = {}
        for question, value in expected:
            key = 'q_%s' % question.id
            data[key] = value

        response = self.client.post(url, data)
        self.assertEqual(302, response.status_code)
        self.assertIn(survey.success_redirect, response._headers['location'][1])

        self.assertEqual(8, Answer.objects.count())
        for question, value in expected:
            answer = Answer.objects.get(question=question)
            self.assertEqual(value, answer.value)

        # -- check with system level submit action
        with self.settings(DFORM_SURVEY_SUBMIT='/foo/'):
            response = self.client.get(url)
            self.assertEqual('/foo/', response.context['submit_action'])

    def test_survey_view(self):
        url_base = '/dform/survey/%s/%s/'
        self._survey_view(url_base, False)

    def test_embedded_survey_view(self):
        url_base = '/dform/embedded_survey/%s/%s/'
        self._survey_view(url_base, True)

    def test_permission_hooks(self):
        hook = 'dform.tests.test_dform.perm_hook'

        with self.settings(DFORM_PERMISSION_HOOK=hook):
            with self.assertRaises(GotHere):
                self.client.post('/dform/survey/1/abc/')

            with self.assertRaises(GotHere):
                self.client.post('/dform/embedded_survey/1/abc/')

            with self.assertRaises(GotHere):
                self.client.post('/dform/sample_survey/1/')

            with self.assertRaises(GotHere):
                self.client.post('/dform/survey_with_answers/1/abc/2/abc/')

            with self.assertRaises(GotHere):
                self.client.post(
                    '/dform/embedded_survey_with_answers/1/abc/2/abc/')

    #---- Survey Answer Views
    def _survey_with_answers(self, url_base, expect_pym):
        survey, fields = self._data_gen()
        questions = list(fields.values())
        expected = list(zip(questions, ['mt', 'tx', 'a', 'c', 'e,f', 2, 42, 
            13.69]))
        del questions[4]
        expected2 = list(zip(questions,['mt2', 'tx2', 'b', 'd', 3, 43, 18.62]))

        ag = AnswerGroup.factory(survey_version=survey.latest_version)
        for question, value in expected:
            survey.answer_question(question, ag, value)

        url = url_base % (survey.latest_version.id, survey.token, ag.id, 
            ag.token)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual('survey', response.context['title'])
        self.assertTemplateUsed(response, 'dform/survey.html')

        # verify pym.js is included or absent as expected
        found_pym = RE_PYM.search(response.content.decode('utf-8'))
        if expect_pym:
            self.assertEqual(None, found_pym)
        else:
            self.assertFalse(found_pym)

        form = response.context['form']
        self.assertEqual(8, len(form.fields))
        for question, value in expected:
            key = 'q_%s' % question.id
            field = form.fields[key]
            self.assertEqual(value, field.initial)

        # -- test change in values, including emptying out a field (no cb)
        data = {}
        for question, value in expected2:
            key = 'q_%s' % question.id
            data[key] = value

        response = self.client.post(url, data)
        self.assertEqual(302, response.status_code)
        self.assertIn(survey.success_redirect, response._headers['location'][1])

        self.assertEqual(7, Answer.objects.count())
        for question, value in expected2:
            answer = Answer.objects.get(question=question)
            self.assertEqual(value, answer.value)

        # once more with a lot of missing fields to trigger the answer delete
        # handling
        data = {
            'q_%s' % fields['multitext'].id:'mt3',
        }

        response = self.client.post(url, data)
        self.assertEqual(302, response.status_code)
        self.assertIn(survey.success_redirect, response._headers['location'][1])

        self.assertEqual(1, Answer.objects.count())
        answer = Answer.objects.get(question=expected[0][0])
        self.assertEqual('mt3', answer.value)

        # -- check with system level submit action
        with self.settings(DFORM_SURVEY_WITH_ANSWERS_SUBMIT='/foo/'):
            response = self.client.get(url)
            self.assertEqual('/foo/', response.context['submit_action'])

    def test_survey_with_answers(self):
        url_base = '/dform/survey_with_answers/%s/%s/%s/%s/'
        self._survey_with_answers(url_base, False)

    def test_embedded_survey_with_answers(self):
        url_base = '/dform/embedded_survey_with_answers/%s/%s/%s/%s/'
        self._survey_with_answers(url_base, True)


class FormTest(TestCase):
    def test_form(self):
        # coverage for edge cases not covered by SurveyViewTests

        with self.assertRaises(AttributeError):
            SurveyForm(initial={'foo':'bar'}, survey_version=None)

        survey = Survey.factory(name='survey', success_redirect='/foo/')
        survey.add_question(Text, '1st question')
        form = SurveyForm(survey_version=survey.latest_version)

        self.assertFalse(form.has_required())

        survey.add_question(Text, '2nd question', required=True)
        form = SurveyForm(survey_version=survey.latest_version)

        self.assertTrue(form.has_required())
