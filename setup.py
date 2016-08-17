import os

VERSION = '0.6.0'

readme = os.path.join(os.path.dirname(__file__), 'README.rst')
long_description = open(readme).read()

SETUP_ARGS = dict(
    name='django-dform',
    version=VERSION,
    description=('Django app for dynamic forms or surveys that can be '
        'injected in sites'),
    long_description=long_description,
    url='https://github.com/cltrudeau/django-dform',
    author='Christopher Trudeau',
    author_email='ctrudeau+pypi@arsensa.com',
    license='MIT',
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='django,form,survey',
    test_suite="load_tests.get_suite",
    install_requires=[
        'Django>=1.8',
        'django-awl>=0.13',
        'wrench>=0.9',
        'jsonfield>=1.0.3',
    ],
    tests_require=[
        'mock>=2.0.0',
    ]
)

if __name__ == '__main__':
    from setuptools import setup, find_packages

    SETUP_ARGS['packages'] = find_packages()
    setup(**SETUP_ARGS)
