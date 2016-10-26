import json, logging
from collections import OrderedDict
from functools import wraps

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.template import Context, Template

from awl.decorators import post_required
from wrench.utils import dynamic_load

from .forms import SurveyForm
from .models import (EditNotAllowedException, Survey, SurveyVersion, Question,
    AnswerGroup)

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
# Admin Methods 
# ============================================================================

@staff_member_required
@post_required(['delta'])
def survey_delta(request, survey_version_id):
    delta = json.loads(request.POST['delta'], object_pairs_hook=OrderedDict)
    if survey_version_id == '0':
        # new survey
        survey = Survey.factory(name=delta['name'])
        version = survey.latest_version
    else:
        version = get_object_or_404(SurveyVersion, id=survey_version_id)

    response = {
        'success':True,
    }

    try:
        version.replace_from_dict(delta)
    except ValidationError as ve:
        response['success'] = False
        response['errors'] = ve.params
    except EditNotAllowedException:
        raise Http404('Survey %s is not editable' % version.survey)
    except Question.DoesNotExist as dne:
        raise Http404('Bad question id: %s' % dne)

    # issue a 200 response
    return JsonResponse(response)


@staff_member_required
def survey_editor(request, survey_version_id):
    if survey_version_id == '0':
        # new survey
        survey = Survey.factory(name='New Survey')
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

    return render(request, 'dform/edit_survey.html', data)


@staff_member_required
def new_version(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    survey.new_version()

    admin_link = reverse('admin:index')
    return_url = request.META.get('HTTP_REFERER', admin_link)
    return HttpResponseRedirect(return_url)


@staff_member_required
def survey_links(request, survey_version_id):
    """Shows links and embedding code for pointing to this survey on an HTML
    page.
    """
    version = get_object_or_404(SurveyVersion, id=survey_version_id)

    survey_url = request.build_absolute_uri(
        reverse('dform-survey', args=(version.id, version.survey.token)))
    embedded_survey_url = request.build_absolute_uri(
        reverse('dform-embedded-survey', args=(version.id, 
        version.survey.token)))
    survey_latest_url = request.build_absolute_uri(
        reverse('dform-survey-latest', args=(version.survey.id, 
        version.survey.token)))
    embedded_survey_latest_url = request.build_absolute_uri(
        reverse('dform-embedded-survey-latest', args=(version.survey.id, 
        version.survey.token)))
    pym_url = request.build_absolute_uri(
        staticfiles_storage.url('dform/js/pym.min.js'))
    
    data = {
        'title':'Links for: %s' % version.survey.name,
        'survey_url':survey_url,
        'embedded_survey_url':embedded_survey_url,
        'survey_latest_url':survey_latest_url,
        'embedded_survey_latest_url':embedded_survey_latest_url,
        'pym_url':pym_url,
        'version':version,
    }

    return render(request, 'dform/links_survey.html', data)


@staff_member_required
def answer_links(request, answer_group_id):
    """Shows links and embedding code for pointing to this AnswerGroup on an 
    HTML page so a user could edit their data.
    """
    answer_group = get_object_or_404(AnswerGroup, id=answer_group_id)
    survey_url = request.build_absolute_uri(
        reverse('dform-survey-with-answers', args=(
            answer_group.survey_version.id, 
            answer_group.survey_version.survey.token, answer_group.id, 
            answer_group.token)))
    
    data = {
        'title':'Answer Links for: %s' % (
            answer_group.survey_version.survey.name),
        'survey_url':survey_url,
    }

    return render(request, 'dform/links_answers.html', data)

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

    return render(request, 'dform/survey.html', data)

# -------------------

def _survey_view(request, survey_version_id, token, is_embedded):
    """General view code for handling a survey, called by survey() or
    embedded_survey()
    """
    version = get_object_or_404(SurveyVersion, id=survey_version_id,
        survey__token=token)

    if request.method == 'POST':
        form = SurveyForm(request.POST, survey_version=version, 
            ip_address=request.META['REMOTE_ADDR'])
        if form.is_valid():
            form.save()

            name = getattr(settings, 'DFORM_SUBMIT_HOOK', '')
            if name:
                fn = dynamic_load(name)
                fn(form)

            return HttpResponseRedirect(version.on_success())
    else:
        form = SurveyForm(survey_version=version)

    try:
        # check if we have an alternate submit mechanism defined
        template = Template(settings.DFORM_SURVEY_SUBMIT)
        context = Context({'survey_version':version})
        submit_action = template.render(context)
    except AttributeError:
        # use our default submit url
        name = 'dform-embedded-survey' if is_embedded else 'dform-survey'
        submit_action = reverse(name, args=(version.id, version.survey.token))

    data = {
        'title':version.survey.name,
        'survey_version':version,
        'form':form,
        'is_embedded':is_embedded,
        'submit_action':submit_action,
    }

    return render(request, 'dform/survey.html', data)


@permission_hook
def survey(request, survey_version_id, token):
    """View for submitting the answers to a survey version.

    URL name reference for this view: ``dform-survey``

    """
    return _survey_view(request, survey_version_id, token, False)


@permission_hook
def embedded_survey(request, survey_version_id, token):
    """View for submitting the answers to a survey version with additional
    Javascript handling for being embedded in an iframe.

    URL name reference for this view: ``dform-survey``

    """
    return _survey_view(request, survey_version_id, token, True)


@permission_hook
def survey_latest(request, survey_id, token):
    """View for submitting the answers to the latest version of a survey.

    URL name reference for this view: ``dform-survey``

    """
    survey = get_object_or_404(Survey, id=survey_id, token=token)
    return _survey_view(request, survey.latest_version.id, token, False)


@permission_hook
def embedded_survey_latest(request, survey_id, token):
    """View for submitting the answers to the latest version of a survey with 
    additional Javascript handling for being embedded in an iframe.

    URL name reference for this view: ``dform-survey``

    """
    survey = get_object_or_404(Survey, id=survey_id, token=token)
    return _survey_view(request, survey.latest_version.id, token, True)

#------------------

def _survey_with_answers_view(request, survey_version_id, survey_token, 
        answer_group_id, answer_token, is_embedded):
    """General view code for editing answer for a survey.  Called by
    survey_with_answers() and embedded_survey_with_answers()
    """
    version = get_object_or_404(SurveyVersion, id=survey_version_id, 
        survey__token=survey_token)
    answer_group = get_object_or_404(AnswerGroup, id=answer_group_id,
        token=answer_token)

    if request.method == 'POST':
        form = SurveyForm(request.POST, survey_version=version,
            answer_group=answer_group)
        if form.is_valid():
            form.save()

            name = getattr(settings, 'DFORM_EDIT_HOOK', '')
            if name:
                fn = dynamic_load(name)
                fn(form)

            return HttpResponseRedirect(version.on_success())
    else:
        form = SurveyForm(survey_version=version, answer_group=answer_group)

    try:
        # check for alternate survey edit handler
        template = Template(settings.DFORM_SURVEY_WITH_ANSWERS_SUBMIT)
        context = Context({
            'survey_version':version, 
            'answer_group':answer_group
        })
        submit_action = template.render(context)
    except AttributeError:
        # use default survey edit handler
        name = 'dform-survey-with-answers' if is_embedded else \
            'dform-embedded-survey-with-answers' 

        submit_action = reverse(name, args=(version.id, version.survey.token, 
            answer_group.id, answer_group.token))

    data = {
        'title':version.survey.name,
        'survey_version':version,
        'answer_group':answer_group,
        'form':form,
        'is_embedded':is_embedded,
        'submit_action':submit_action,
    }

    return render(request, 'dform/survey.html', data)


@permission_hook
def survey_with_answers(request, survey_version_id, survey_token, 
        answer_group_id, answer_token):
    """View for viewing and changing the answers to a survey that already has
    answers.

    URL name reference for this view: ``dform-survey-with-answers``
    """
    return _survey_with_answers_view(request, survey_version_id, survey_token,
        answer_group_id, answer_token, False)


@permission_hook
def embedded_survey_with_answers(request, survey_version_id, survey_token, 
        answer_group_id, answer_token):
    """View for viewing and changing the answers to a survey that already has
    answers with additional Javascript for being handled in an iframe.

    URL name reference for this view: ``dform-survey-with-answers``
    """
    return _survey_with_answers_view(request, survey_version_id, survey_token,
        answer_group_id, answer_token, True)
