import json, logging
from collections import OrderedDict
from functools import wraps

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.template import Context, Template

from awl.decorators import post_required
from awl.utils import render_page
from wrench.utils import dynamic_load

from .fields import FIELDS_DICT
from .forms import SurveyForm
from .models import (EditNotAllowedException, Survey, SurveyVersion, Question,
    QuestionOrder, AnswerGroup)

logger = logging.getLogger(__name__)

# ============================================================================
# Security Decorator
# ============================================================================

def permission_hook(target):
    @wraps(target)
    def wrapper(*args, **kwargs):
        if hasattr(settings, 'DFORM_PERMISSION_HOOK'):
            fn = dynamic_load(settings.DFORM_PERMISSION_HOOK)
            fn(target.__name__, *args, **kwargs)

        # everything verified, run the view
        return target(*args, **kwargs)
    return wrapper

# ============================================================================
# AJAX Methods 
# ============================================================================

@staff_member_required
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
        version.replace_from_dict(delta)
    except EditNotAllowedException:
        raise Http404('Survey %s is not editable' % version.survey)
    except Question.DoesNotExist as dne:
        raise Http404('Bad question id: %s' % dne)

    # issue a 200 response
    return HttpResponse()


@staff_member_required
def survey_editor(request, survey_version_id):
    if survey_version_id == '0':
        # new survey
        survey = Survey.objects.create(name='New Survey')
        version = survey.latest_version
    else:
        version = get_object_or_404(SurveyVersion, id=survey_version_id)

    admin_link = reverse('admin:index')
    return_url = request.META.get('HTTP_REFERER', admin_link)
    save_url = reverse('dform-survey-delta', args=(version.id, ))
    data = {
        'survey_version':json.dumps(version.to_dict()),
        'save_url':save_url,
        'return_url':return_url,
    }

    return render_page(request, 'dform/edit_survey.html', data)


@staff_member_required
def new_version(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    survey.new_version()

    admin_link = reverse('admin:index')
    return_url = request.META.get('HTTP_REFERER', admin_link)
    return HttpResponseRedirect(return_url)

# ============================================================================
# Form Views
# ============================================================================

@permission_hook
def sample_survey(request, survey_version_id):
    """A view for displaying a sample version of a form.  The submit mechanism
    does nothing.

    URL name reference for this view: ``dform-sample-survey``

    :param survey_version_id:
        Id of a :class:`SurveyVersion` object
    """
    version = get_object_or_404(SurveyVersion, id=survey_version_id)

    form = SurveyForm(survey_version=version)
    data = {
        'title':'Sample: %s' % version.survey.name,
        'survey_version':version,
        'form':form,
        'submit_action':'',
    }

    return render_page(request, 'dform/survey.html', data)


@permission_hook
def survey(request, survey_version_id):
    """View for submitting the answers to a survey.

    URL name reference for this view: ``dform-survey``

    """
    version = get_object_or_404(SurveyVersion, id=survey_version_id)

    try:
        template = Template(settings.DFORM_SURVEY_SUBMIT)
        context = Context({'survey_version':version})
        submit_action = template.render(context)
    except AttributeError:
        submit_action = reverse('dform-survey', args=(version.id, ))

    if request.method == 'POST':
        form = SurveyForm(request.POST, survey_version=version)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(version.on_success())
    else:
        form = SurveyForm(survey_version=version)

    data = {
        'title':version.survey.name,
        'survey_version':version,
        'form':form,
        'submit_action':submit_action,
    }

    return render_page(request, 'dform/survey.html', data)


@permission_hook
def survey_with_answers(request, survey_version_id, answer_group_id):
    """View for viewing and changing the answers to a survey that already has
    answers.

    URL name reference for this view: ``dform-survey-with-answers``
    """
    version = get_object_or_404(SurveyVersion, id=survey_version_id)
    answer_group = get_object_or_404(AnswerGroup, id=answer_group_id)

    try:
        template = Template(settings.DFORM_SURVEY_WITH_ANSWERS_SUBMIT)
        context = Context({
            'survey_version':version, 
            'answer_group':answer_group
        })
        submit_action = template.render(context)
    except AttributeError:
        submit_action = reverse('dform-survey-with-answers', args=(
            version.id, answer_group.id))

    if request.method == 'POST':
        form = SurveyForm(request.POST, survey_version=version,
            answer_group=answer_group)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(version.on_success())
    else:
        form = SurveyForm(survey_version=version, answer_group=answer_group)

    data = {
        'title':version.survey.name,
        'survey_version':version,
        'answer_group':answer_group,
        'form':form,
        'submit_action':submit_action,
    }

    return render_page(request, 'dform/survey.html', data)
