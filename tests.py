#!/usr/bin/env python
import os, sys
import django

from django.conf import settings
from django.test.runner import DiscoverRunner

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dform'))

settings.configure(DEBUG=True,
    BASE_DIR=BASE_DIR,
    DATABASES={
        'default':{
            'ENGINE':'django.db.backends.sqlite3',
        }
    },
    ROOT_URLCONF='dform.urls',
    MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    ),
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
        'awl',
        'dform',
    ),
    TEMPLATE_DIRS = (
        os.path.abspath(os.path.join(BASE_DIR, 'dform/templates')),
    )
)

django.setup()
runner = DiscoverRunner(verbosity=1)
failures = runner.run_tests(['dform'])
if failures:
    sys.exit(failures)
