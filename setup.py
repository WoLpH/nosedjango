from setuptools import setup, find_packages, Command
import os, subprocess, sys

class RunTests(Command):
    description = "Run the test suite from the tests dir."
    user_options = []
    extra_env = {}

    def run(self):
        for env_name, env_value in self.extra_env.items():
            os.environ[env_name] = str(env_value)

        setup_dir = os.path.abspath(os.path.dirname(__file__))
        tests_dir = os.path.join(setup_dir, 'nosedjangotests')
        os.chdir(tests_dir)
        sys.path.append(tests_dir)

        try:
            from nose.core import TestProgram
            import nosedjango
        except ImportError:
            print 'nose and nosedjango are required to run this test suite'
            sys.exit(1)

        print "Running tests with sqlite"
        args = [
            '-v',
            '--with-doctest',
            '--with-django',
            '--django-settings', 'nosedjangotests.settings',
            '--django-sqlite',
            'nosedjangotests.polls',
        ]
        TestProgram(argv=args, exit=False)

        print "Running tests multiprocess"
        args = [
            '-v',
            '--with-doctest',
            '--processes', '3',
            '--with-django',
            '--django-settings', 'nosedjangotests.settings',
            '--django-sqlite',
            'nosedjangotests.polls',
        ]
        TestProgram(argv=args, exit=False)

        print "Running tests with mysql. (will fail if mysql not configured)"
        args = [
            '-v',
            '--with-id',
            '--with-doctest',
            '--with-django',
            '--django-settings', 'nosedjangotests.settings',
            'nosedjangotests.polls',
        ]
        TestProgram(argv=args, exit=False)

        os.chdir(setup_dir)

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


setup(
    name='NoseDjango',
    version='0.7.2',
    author='Jyrki Pulliainen',
    author_email = 'jyrki.pulliainen@inoi.fi',
    description = 'nose plugin for easy testing of django projects ' \
        'and apps. Sets up a test database (or schema) and installs apps ' \
        'from test settings file before tests are run, and tears the test ' \
        'database (or schema) down after all tests are run.',
    install_requires='nose>=0.11',
    url = "http://www.assembla.com/spaces/nosedjango",
    license = 'GNU LGPL',
    packages = find_packages(exclude=['nosedjangotests', 'nosedjangotests.*']),
    zip_safe = False,
    cmdclass = {'nosetests': RunTests},
    include_package_data = True,
    entry_points = {
        'nose.plugins': [
            'django = nosedjango.nosedjango:NoseDjango',
            'cherrypyliveserver = nosedjango.plugins.cherrypy_plugin:CherryPyLiveServerPlugin',
            'djangofilestorage = nosedjango.plugins.file_storage_plugin:FileStoragePlugin',
            'selenium = nosedjango.nosedjango:SeleniumPlugin',
            'djangosphinx = nosedjango.plugins.sphinx:SphinxPlugin',
            'sshtunnel = nosedjango.nosedjango:SshTunnelPlugin',
            ]
        }
    )

