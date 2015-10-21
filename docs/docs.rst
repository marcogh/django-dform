Configuration
*************

Permission Hook
===============

Out-of-the-box, DForm comes with two sets of URL files.  This is done to split
up the admin-only views that are used for creating and editing surveys, and
the views provided for submitting surveys.  Depending on your usage patterns
and security concerns you may not want to include all of the URLs in the
second set of views.

Each of the submission views has a built in permissions hook.  This allows you
to define a function that is called for each call to the submission views.

In your ``settings.py`` file:

.. code-block:: python

    DFORM_PERMISSION_HOOK = 'special.my_hook'

The ``DFORM_PERMISSION_HOOK`` value is set to the fully dot-qualified name of
a function in a module.  The function will be called with the name of the view
being checked as well as all of the arguments for the view.

An example hook:

.. code-block:: python

    # special.py

    import logging
    from django.http import Http404

    logger = logging.getLogger(__name__)

    def my_hook(name, *args):
        request = args[0]
        if name == 'survey_with_answers':
            logger.debug('survey_with_answers: version=%s answer_group=%s',
                args[1], args[2])
            raise Http404
        elif name == 'sample_survey':
            logger.debug('sample_survey: version=%s', args[1])
        elif name == 'survey':
            logger.debug('survey: version=%s', args[1])

The hook defined above will allow anyone to submit a survey or view a sample,
but if they attempt to call the view that changes answers a 404 is raised.
This is overly simplistic as it would stop even the admin from changing the
values.

Alternatively, you could write your own views that wrap calls to the survey
submission views.  If you do this and define the URLs with the appropriate
names the admin links should still work.  See :doc:`views` for the URL name
references for each of the views.

Wrapping Survey Submission Views
--------------------------------

The built-in survey submission views set the HTML form action attribute to
themselves.  To change where the forms submit to add settings:

.. code-block:: python

    DFORM_SURVEY_SUBMIT = '/my_survey/{{survey_version.id}}/'
    DFORM_SURVEY_WITH_ANSWERS_SUBMIT = \
        '/my_survey_with_answers/{{survey_version.id}}/{{answer_group.id}}/'

These settings are processed through the Django template mechanism with a
context of the :class:`.SurveyVersion` and 
:class:`.AnswerGroup` as appropriate.


Survey Submission Success
=========================

The buit-in survey submission views support several different ways of
determining where to redirect to after a successful submission.  The first is
through settings:

.. code-block:: python

    DFORM_SUCCESS_REDIRECT = '/after_submit/'

The second mechanism is the ``success_redirect`` field on the :class:`.Survey`
object.  If this value is set it overrides any settings configuration.
Similarly, the ``success_redirect`` field on the :class`SurveyVersion`
overrides the field of the same name on the parent :class:`.Survey` and value
for settings.

If none of these are set for a given survey version an :class:`.AttributeError`
is raised.
