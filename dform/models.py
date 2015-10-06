# dform.models.py
import logging, collections

from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.encoding import python_2_unicode_compatible

from jsonfield import JSONField
from awl.models import TimeTrackModel
from awl.rankedmodel.models import RankedModel

from .fields import FIELD_CHOICES, FIELDS_DICT

logger = logging.getLogger(__name__)

# ============================================================================
# Survey Management
# ============================================================================

class EditNotAllowedException(Exception):
    pass


@python_2_unicode_compatible
class Survey(TimeTrackModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return 'Survey(id=%s %s)' % (self.id, self.name)

    def add_question(self, field, text, rank=0, required=False, 
            field_parms={}, version=None):
        """Creates a new :class:`Question` for the ``Survey``.

        :param field: 
            a :class:`Field` instance describing the kind of question being
            created
        :param text:
            text to display when asking the question
        :param rank:
            the order number of this question, defaults to 0 which means
            insert last
        :param required:
            whether the question is required for form submission
        :param field_parms:
            a field specific dictionary specifying parameters for the use of
            the field.  
        :param version:
            version of the ``Survey`` to add the question to; defaults to the
            latest version
        :returns:
            newly created :class:`Question` object
        :raises EditNotAllowedException:
            editing is not allowed for surveys that already have answers
        """
        if not version:
            version = self.latest_version

        version.validate_editable()

        field.check_field_parms(field_parms)
        question = Question.objects.create(survey=self, text=text,
            field_key=field.field_key, required=required,
            field_parms=field_parms)
        question.survey_versions.add(version)

        kwargs = {
            'survey_version':version,
            'question':question,
        }
        if rank != 0:
            kwargs['rank'] = rank

        QuestionOrder.objects.create(**kwargs)
        return question

    def remove_question(self, question, version=None):
        """Removes the given question from the given version of the ``Survey``. 

        :param question:
            :class:`Question` to be removed
        :param version:
            version of the ``Survey`` from which to remove the question;
            defaults to the latest version
        :raises EditNotAllowedException:
            editing is not allowed for surveys that already have answers
        """
        if not version:
            version = self.latest_version

        version.validate_editable()
        question.survey_versions.remove(version)
        QuestionOrder.objects.get(question=question, 
            survey_version=version).delete()

    @property
    def latest_version(self):
        return SurveyVersion.objects.filter(survey=self).order_by(
            '-version_num')[0]

    def questions(self, version=None):
        """Returns an iterable of the questions for the given version
        of this survey in order.

        :param version:
            version of the ``Survey`` to get the questions from; defaults to
            the latest version
        :returns:
            list of :class:`Question` objects
        """
        if not version:
            version = self.latest_version

        orders = QuestionOrder.objects.filter(survey_version=version
            ).order_by('rank')
        return [order.question for order in orders]

    def answer_question(self, question, answer_group, value, version=None):
        """Record an answer to the given question.

        :param question:
            :class:`Question` that is being answered.  It must be a valid
            question for this version of the survey
        :param answer_group:
            A number that groups together the answers for a survey.  An
            example would be to use the user's id so that all of their answers
            are grouped together.  This would mean each user could only answer
            each survey once.
        :param value:
            Value to record as an answer.  The value is validated against the
            field associated with the :class:`Question`.
        :param version:
            The version of the ``Survey` to record the answer.  If not given,
            defaults to the latest version.

        :raises ValidationError:
            If the value given does not pass the question's field's validation
        :raises AttributeError:
            If the question is not attached to this version of the
            ``Survey``
        """
        if not version:
            version = self.latest_version

        try:
            question.survey_versions.get(id=version.id)
        except SurveyVersion.DoesNotExist:
            raise AttributeError()

        return Answer.factory(version, question, answer_group, value)

    @transaction.atomic
    def new_version(self):
        """Creates a new version of the ``Survey``, associating all the
        current verion's questions with the new version.  Note, this will have
        the side effect of changing the latest version of this ``Survey``.

        :returns:
            newly created :class:`SurveyVersion`
        """
        old_version = self.latest_version
        new_version = SurveyVersion.objects.create(survey=self,
            version_num=self.latest_version.version_num + 1)

        orders = QuestionOrder.objects.filter(
            survey_version=old_version).order_by('rank')
        for order in orders:
            QuestionOrder.objects.create(survey_version=new_version,
                question=order.question, rank=order.rank)
            order.question.survey_versions.add(new_version)

        return new_version

    def to_dict(self, version=None):
        """Returns a dictionary representation of the given version.

        :param version:
            The version of the ``Survey` to turn into a dictionary, defaults
            to the latest version.

        Format:

        .. code-block::python

            {
                'name':survey_name,
                'questions':[
                    {
                        'id':question_id,
                        'field_key':question_field_key,
                        'text':question_text,
                        'required':is_question_required,
                        'field_params:OrderedDict(*field_parm_tuples),
                    }
                ]
            }

        .. note::

            The order of the question dictionaries will be the order of the
            questions in the survey.

        .. note::

            Be careful to use a ``OrderedDict`` with the field parameters, as
            the order of parameters is used for the order of display in
            multiple choice style questions.
        """
        if not version:
            version = self.latest_version

        questions = []
        for question in version.survey.questions(version):
            questions.append({
                'id':question.id,
                'field_key':question.field_key,
                'text':question.text,
                'required':question.required,
                'field_parms':question.field_parms,
            })

        data = {
            'name':version.survey.name,
            'questions':questions,
        }

        return data

    def replace_from_dict(self, data, version=None):
        """Takes the given dictionary and modifies the survey version and its
        associated questions.  Uses the same format as :func:`Survey.to_dict`
        with one additional (optional) key "remove" which contains a list of
        :class:`Question` ids to be removed from the ``Survey``.

        :param data:
            Dictionary to overwrite the contents of the ``Survey` and
            associated :class:`Question` objects with.
        :param version:
            The version of the ``Survey` to replace with the "data"
            dictionary, defaults to the latest version.
        :raises EditNotAllowedException:
            If the version being replaced is active
        :raises Question.DoesNotExist:
            If a question id is referenced that does not exist or is not
            associated with this survey.
        """
        if not version:
            version = self.latest_version

        version.validate_editable()

        if 'name' in data:
            self.name = data['name']
            self.save()

        if 'questions' in data:
            for q_data in data['questions']:
                if q_data['id'] == 0:
                    # new question
                    kwargs = {
                        'field':FIELDS_DICT[q_data['field_key']],
                        'text':q_data['text'],
                        'required':q_data['required'],
                        'field_parms':q_data['field_parms'],
                        'version':version,
                    }

                    # add the question and set the data's question id so that we
                    # can do re-ordering down below
                    question = self.add_question(**kwargs)
                    q_data['id'] = question.id
                else:
                    question = Question.objects.get(id=q_data['id'], 
                        survey__id=self.id)

                    question.text = q_data['text']
                    question.required = q_data['required']
                    question.field_parms = q_data['field_parms']
                    question.save()

        # fix the ranking -- creating new questions will mess with the order
        if 'questions' in data:
            for index, q_data in enumerate(data['questions']):
                question = Question.objects.get(id=q_data['id'], 
                    survey__id=self.id)
                q_order = QuestionOrder.objects.get(question=question,
                    survey_version=version)
                q_order.rank = index + 1
                q_order.save(rerank=False)

        if 'remove' in data:
            for id in data['remove']:
                question = Question.objects.get(id=id, survey__id=self.id)
                self.remove_question(question, version)


@receiver(post_save, sender=Survey)
def survey_post_save(sender, **kwargs):
    if kwargs['created']:
        # newly created object, create a version to go with it
        SurveyVersion.objects.create(survey=kwargs['instance'])


@python_2_unicode_compatible
class SurveyVersion(TimeTrackModel):
    survey = models.ForeignKey(Survey)
    version_num = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return 'SurveyVersion(id=%s survey=%s, num=%s)' % (self.id, 
            self.survey.name, self.version_num)

    class Meta:
        verbose_name = 'Survey Version'

    def validate_editable(self):
        if Answer.objects.filter(survey_version=self).count() != 0:
            raise EditNotAllowedException()

    def is_editable(self):
        return Answer.objects.filter(survey_version=self).count() == 0

# ============================================================================
# Question & Answers
# ============================================================================

@python_2_unicode_compatible
class Question(TimeTrackModel):
    survey = models.ForeignKey(Survey)
    survey_versions = models.ManyToManyField(SurveyVersion)

    text = models.TextField(blank=True)
    field_key = models.CharField(max_length=2, choices=FIELD_CHOICES)
    field_parms = JSONField(default={}, 
        load_kwargs={'object_pairs_hook':collections.OrderedDict})
    required = models.BooleanField(default=False)

    def __str__(self):
        return 'Question(id=%s %s:%s)' % (self.id, self.field_key,
            self.short_text)

    @property
    def field(self):
        return FIELDS_DICT[self.field_key]

    @property
    def short_text(self):
        """Returns a short version of the question text.  Any thing longer
        than 15 characters is truncated with an elipses."""
        text = self.text
        if len(text) >= 15:
            text = text[:12] + '...'

        return text


@python_2_unicode_compatible
class QuestionOrder(TimeTrackModel, RankedModel):
    survey_version = models.ForeignKey(SurveyVersion)
    question = models.ForeignKey(Question)

    class Meta:
        verbose_name = 'Question Order'
        verbose_name_plural = 'Question Order'
        ordering = ['survey_version__id', 'rank']

    def __str__(self):
        return 'QuestionOrder(id=%s, rank=%s sv.id=%s q.id=%s)' % (self.id,
            self.rank, self.survey_version.id, self.question.id)

    def grouped_filter(self):
        return QuestionOrder.objects.filter(
            survey_version=self.survey_version).order_by('rank')


@python_2_unicode_compatible
class Answer(TimeTrackModel):
    question = models.ForeignKey(Question)
    survey_version = models.ForeignKey(SurveyVersion)

    answer_group = models.PositiveSmallIntegerField()

    answer_text = models.TextField(blank=True)
    answer_key = models.CharField(max_length=32, blank=True)
    answer_float = models.FloatField(null=True, blank=True)

    def __str__(self):
        return 'Answer(id=%s q.id=%s value=%s)' % (self.id, self.question.id,
            self.display_value)

    @classmethod
    def factory(cls, survey_version, question, answer_group, value):
        question.field.check_value(question.field_parms, value)
        kwargs = {
            'survey_version':survey_version,
            'question':question,
            'answer_group':answer_group,
        }
        kwargs[question.field.storage_key] = value
        return Answer.objects.create(**kwargs)

    @property
    def value(self):
        """Returns the value stored in this ``Answer``.  Note that the type of
        the data returned may be a string or float depending on what is
        stored.
        """
        return getattr(self, self.question.field.storage_key)

    @property
    def display_value(self):
        """Returns a string version of the value limited to 15 characters.
        """
        value = str(self.value)
        if len(value) >= 15:
            value = value[:12] + '...'

        return value
