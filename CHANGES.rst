0.8.1
=====

* fixed: Email field was missing from survey editor

0.8.0
=====

* implement submit and edit call-back hooks
* add Google reCAPTCHA capabilities
* added views for getting latest survey
* added Email field
* added IP Address tracking on the survey submit

0.7.0
=====

* changed "Add Survey" button in django admin to use Survey Editor

0.6.1
=====

* made python 3.5 and django 1.10 compatible
* fixed missing migrations

0.5
===

* changed over survey links to now use a dedicated token, not secure but helps
    prevent cross survey guessing based on the URL
* added admin pages for showing sample HTML to paste into your web pages to
    link to or embed a survey
* added use of pym.js to handle responsive pages when doing a embedded IFRAME
    inclusion of a form
* removed a bunch of unused imports

0.3
===

* finished tests, now supports python 2.7

0.2
===

* finished main feature set
* added documentation

0.1
===

* initial commit to pypi
