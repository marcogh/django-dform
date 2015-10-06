import json, logging
from collections import OrderedDict
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404

from awl.decorators import post_required
from awl.utils import render_page

from .fields import FIELDS_DICT
from .models import (EditNotAllowedException, Survey, SurveyVersion, Question,
    QuestionOrder)

logger = logging.getLogger(__name__)

# ============================================================================
# AJAX Methods 
# ============================================================================

@post_required(['delta'])
def survey_delta(request, survey_version_id):
    delta = json.loads(request.POST['delta'], object_pairs_hook=OrderedDict)
    if survey_version_id == '0':
        # new survey
        survey = Survey.objects.create(name=delta['name'])
        version = survey.latest_version
    else:
        version = get_object_or_404(SurveyVersion, id=survey_version_id)
        try:
            version.validate_editable()
        except EditNotAllowedException:
            raise Http404('Survey %s is not editable' % version.survey)

        survey = version.survey

        if 'name' in delta:
            survey.name = delta['name']
            survey.save()

    # have our survey, now process the edits
    if 'questions' in delta:
        for q_delta in delta['questions']:
            if q_delta['id'] == 0:
                # new question
                kwargs = {
                    'field':FIELDS_DICT[q_delta['field_key']],
                    'text':q_delta['text'],
                    'required':q_delta['required'],
                    'field_parms':q_delta['field_parms'],
                    'version':version,
                }

                # add the question and set the delta's question id so that we
                # can do re-ordering down below
                question = survey.add_question(**kwargs)
                q_delta['id'] = question.id
            else:
                question = get_object_or_404(Question, id=q_delta['id'], 
                    survey__id=survey.id)

                question.text = q_delta['text']
                question.required = q_delta['required']
                question.field_parms = q_delta['field_parms']
                question.save()

    # fix the ranking -- creating new questions will mess with the order
    if 'questions' in delta:
        for index, q_delta in enumerate(delta['questions']):
            question = get_object_or_404(Question, id=q_delta['id'], 
                survey__id=survey.id)
            q_order = QuestionOrder.objects.get(question=question,
                survey_version=version)
            q_order.rank = index + 1
            q_order.save(rerank=False)

    if 'remove' in delta:
        for id in delta['remove']:
            question = get_object_or_404(Question, id=id, survey__id=survey.id)
            survey.remove_question(question, version)

    # issue a 200 response
    return HttpResponse()
