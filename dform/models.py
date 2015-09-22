# dform.models.py
import logging

from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from jsonfield import JSONField
from awl.rankedmodel.models import RankedModel

from .fields import FIELD_CHOICES, FIELDS_DICT

logger = logging.getLogger(__name__)

# ============================================================================

class TimeTrackedModel(models.Model):
    """Abstract model for create & update fields.  """
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# ============================================================================
# Survey Management
# ============================================================================

class EditNotAllowedException(Exception):
    pass


class Survey(TimeTrackedModel):
    name = models.CharField(max_length=50)

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


@receiver(post_save, sender=Survey)
def survey_post_save(sender, **kwargs):
    if kwargs['created']:
        # newly created object, create a version to go with it
        SurveyVersion.objects.create(survey=kwargs['instance'])


class SurveyVersion(TimeTrackedModel):
    survey = models.ForeignKey(Survey)
    version_num = models.PositiveSmallIntegerField(default=1)

    def validate_editable(self):
        if Answer.objects.filter(survey_version=self).count() != 0:
            raise EditNotAllowedException()

# ============================================================================
# Question & Answers
# ============================================================================

class Question(TimeTrackedModel):
    survey = models.ForeignKey(Survey)
    survey_versions = models.ManyToManyField(SurveyVersion)

    text = models.TextField(blank=True)
    field_key = models.CharField(max_length=2, choices=FIELD_CHOICES)
    field_parms = JSONField(default={})
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


class QuestionOrder(TimeTrackedModel, RankedModel):
    survey_version = models.ForeignKey(SurveyVersion)
    question = models.ForeignKey(Question)

    def grouped_filter(self):
        return QuestionOrder.objects.filter(
            survey_version=self.survey_version).order_by('rank')


class Answer(TimeTrackedModel):
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
