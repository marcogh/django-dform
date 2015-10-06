#!/usr/bin/env python

import sys
import django

from django.conf import settings
from django.test.runner import DiscoverRunner

settings.configure(DEBUG=True,
    DATABASES={
        'default':{
            'ENGINE':'django.db.backends.sqlite3',
        }
    },
    ROOT_URLCONF='dform.urls',
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
        'awl',
        'dform',
    ),
)

django.setup()
runner = DiscoverRunner(verbosity=1)
failures = runner.run_tests(['dform'])
if failures:
    sys.exit(failures)
