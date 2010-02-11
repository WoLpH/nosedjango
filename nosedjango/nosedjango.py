"""
nose plugin for easy testing of django projects and apps. Sets up a test
database (or schema) and installs apps from test settings file before tests
are run, and tears the test database (or schema) down after all tests are run.
"""

import os, sys, shutil
import re
import subprocess
from time import sleep

from nose.plugins import Plugin
import nose.case

from django.core.files.storage import FileSystemStorage
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import  AdminMediaHandler

# Force settings.py pointer
# search the current working directory and all parent directories to find
# the settings file
from nose.importer import add_path
if not 'DJANGO_SETTINGS_MODULE' in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.core.management import setup_environ

DEFAULT_LIVE_SERVER_ADDRESS = '0.0.0.0'
DEFAULT_LIVE_SERVER_PORT = '8000'

NT_ROOT = re.compile(r"^[a-zA-Z]:\\$")
def get_settings_path(settings_module):
    '''
    Hunt down the settings.py module by going up the FS path
    '''
    cwd = os.getcwd()
    settings_filename = '%s.py' % (
        settings_module.split('.')[-1]
        )
    while cwd:
        if settings_filename in os.listdir(cwd):
            break
        cwd = os.path.split(cwd)[0]
        if os.name == 'nt' and NT_ROOT.match(cwd):
            return None
        elif cwd == '/':
            return None
    return cwd

def _dummy(*args, **kwargs):
    """Dummy function that replaces the transaction functions"""
    return


class NoseDjango(Plugin):
    """
    Enable to set up django test environment before running all tests, and
    tear it down after all tests.

    Note that your django project must be on PYTHONPATH for the settings file
    to be loaded. The plugin will help out by placing the nose working dir
    into sys.path if it isn't already there, unless the -P
    (--no-path-adjustment) argument is set.
    """
    name = 'django'

    def disable_transaction_support(self, transaction):
        self.orig_commit = transaction.commit
        self.orig_rollback = transaction.rollback
        self.orig_savepoint_commit = transaction.savepoint_commit
        self.orig_savepoint_rollback = transaction.savepoint_rollback
        self.orig_enter = transaction.enter_transaction_management
        self.orig_leave = transaction.leave_transaction_management

        transaction.commit = _dummy
        transaction.rollback = _dummy
        transaction.savepoint_commit = _dummy
        transaction.savepoint_rollback = _dummy
        transaction.enter_transaction_management = _dummy
        transaction.leave_transaction_management = _dummy

    def restore_transaction_support(self, transaction):
        transaction.commit = self.orig_commit
        transaction.rollback = self.orig_rollback
        transaction.savepoint_commit = self.orig_savepoint_commit
        transaction.savepoint_rollback = self.orig_savepoint_rollback
        transaction.enter_transaction_management = self.orig_enter
        transaction.leave_transaction_management = self.orig_leave

    def options(self, parser, env):
        parser.add_option('--django-settings',
                          help='Use custom Django settings module.',
                          metavar='SETTINGS',
                          )
        parser.add_option('--django-sqlite',
                          help='Use in-memory sqlite for the tests',
                          dest='use_sqlite', action="store_true",
                          default=False
                          )
        parser.add_option('--xvfb-headless',
                          help="Create an X virtual frame buffer at the given value for use in headless webdriver browser testing",
                          default=None)
        super(NoseDjango, self).options(parser, env)

    def configure(self, options, conf):
        self.verbosity = conf.verbosity
        if options.django_settings:
            self.settings_module = options.django_settings
        elif 'DJANGO_SETTINGS_MODULE' in os.environ:
            self.settings_module = os.environ['DJANGO_SETTINGS_MODULE']
        else:
            self.settings_module = 'settings'

        self._use_sqlite = options.use_sqlite
        self._xvfb_headless = options.xvfb_headless

        super(NoseDjango, self).configure(options, conf)

    def begin(self):
        """Create the test database and schema, if needed, and switch the
        connection over to that database. Then call install() to install
        all apps listed in the loaded settings module.
        """
        os.environ['DJANGO_SETTINGS_MODULE'] = self.settings_module

        if self.conf.addPaths:
            map(add_path, self.conf.where)

        try:
            __import__(self.settings_module)
            self.settings_path = self.settings_module
        except ImportError:
            # Settings module is not found in PYTHONPATH. Try to do
            # some funky backwards crawling in directory tree, ie. add
            # the working directory (and any package parents) to
            # sys.path before trying to import django modules;
            # otherwise, they won't be able to find project.settings
            # if the working dir is project/ or project/..


            self.settings_path = get_settings_path(self.settings_module)

            if not self.settings_path:
                # short circuit if no settings file can be found
                raise RuntimeError("Can't find Django settings file!")

            add_path(self.settings_path)
            sys.path.append(self.settings_path)

        from django.conf import settings

        # If the user passed in --django-sqlite, use an in-memory sqlite db
        if self._use_sqlite:
            settings.DATABASE_ENGINE = 'sqlite3'
            settings.DATABASE_NAME = '' # in-memory database
            settings.DATABASE_OPTIONS = {}
            settings.DATABASE_USER = ''
            settings.DATABASE_PASSWORD = ''

        if self._xvfb_headless:
            try:
                xvfb = subprocess.Popen(['xvfb', ':%s' % self._xvfb_headless, '-ac'], stderr=subprocess.PIPE)
            except OSError:
                # Newer distros use Xvfb
                xvfb = subprocess.Popen(['Xvfb', ':%s' % self._xvfb_headless, '-ac'], stderr=subprocess.PIPE)
            os.environ['DISPLAY'] = ':%s' % self._xvfb_headless

        # Do our custom testrunner stuff
        custom_before()

        # Some Django code paths evaluate differently
        # between DEBUG and not DEBUG.  Example of this include the url
        # dispatcher when 404's are hit.  Django's own test runner forces DEBUG
        # to be off.
        settings.DEBUG = False

        from django.core import management
        from django.test.utils import setup_test_environment

        self.old_db = settings.DATABASE_NAME
        from django.db import connection

        setup_test_environment()

        management.get_commands()
        management._commands['syncdb'] = 'django.core'

        connection.creation.create_test_db(verbosity=self.verbosity)

    def _supports_transactions(self, test, settings):
        """
        Determine if the given test supports transaction management.
        """
        transaction_support = True

        if hasattr(test.context, 'use_transaction'):
            transaction_support = test.context.use_transaction
        if hasattr(settings, 'DISABLE_TRANSACTION_MANAGEMENT'):
            # Do not use transactions if user has forbidden usage.
            # Assume that the database supports them anyway.
            transaction_support = not settings.DISABLE_TRANSACTION_MANAGEMENT
        if hasattr(settings, 'DATABASE_SUPPORTS_TRANSACTIONS'):
            if not settings.DATABASE_SUPPORTS_TRANSACTIONS:
                transaction_support = False

        return transaction_support

    def afterTest(self, test):
        # Restore transaction support on tests
        from django.conf import settings
        from django.db import connection, transaction

        if self._managing_transactions:
            self.restore_transaction_support(transaction)
            transaction.rollback()
            if transaction.is_managed():
                transaction.leave_transaction_management()
            # If connection is not closed Postgres can go wild with
            # character encodings.
            connection.close()

    def beforeTest(self, test):

        if not self.settings_path:
            # short circuit if no settings file can be found
            return

        from django.core.management import call_command
        from django.core.urlresolvers import clear_url_caches
        from django.conf import settings
        from django.db import connection, transaction

        transaction_support = self._supports_transactions(test, settings)
        self._managing_transactions = transaction_support

        if transaction_support:
            transaction.enter_transaction_management()
            transaction.managed(True)
            self.disable_transaction_support(transaction)

        else:
            call_command('flush', verbosity=0, interactive=False)

        if isinstance(test, nose.case.Test) and \
            hasattr(test.context, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                call_command('loaddata', *test.context.fixtures, **{'verbosity': 0})

        if isinstance(test, nose.case.Test) and \
            hasattr(test.context, 'urls'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                self.old_urlconf = settings.ROOT_URLCONF
                settings.ROOT_URLCONF = self.urls
                clear_url_caches()


    def finalize(self, result=None):
        """
        Clean up any created database and schema.
        """
        if not self.settings_path:
            # short circuit if no settings file can be found
            return

        from django.test.utils import teardown_test_environment
        from django.db import connection
        from django.conf import settings

        # Clean up our custom testrunner stuff
        custom_after()

        connection.creation.destroy_test_db(self.old_db, verbosity=self.verbosity)
        teardown_test_environment()

        if hasattr(self, 'old_urlconf'):
            settings.ROOT_URLCONF = self.old_urlconf
            clear_url_caches()

def custom_before():
    setup_fs = SetupTestFilesystem()
    setup_celery = SetupCeleryTesting()
    setup_cache = SetupCacheTesting()

    from django.conf import settings
    settings.DOCUMENT_PRINTING_CACHE_ON_SAVE = False

    setup_fs.before()
    setup_celery.before()
    setup_cache.before()

def custom_after():
    setup_fs = SetupTestFilesystem()
    setup_celery = SetupCeleryTesting()
    setup_cache = SetupCacheTesting()

    setup_fs.after()
    setup_celery.after()
    setup_cache.after()

class TestFileSystemStorage(FileSystemStorage):
        """
        Filesystem storage that puts files in a special test folder that can
        be deleted before and after tests.
        """
        def __init__(self, location=None, base_url=None, *args, **kwargs):
            location = SetupTestFilesystem.TEST_MEDIA_ROOT
            base_url = SetupTestFilesystem.TEST_MEDIA_URL
            return super(TestFileSystemStorage, self).__init__(location, base_url, *args, **kwargs)

class SetupTestFilesystem():
    """
    Set up a test file system so you're writing to a specific directory for your
    testing.
    """
    from django.conf import settings
    TEST_MEDIA_ROOT = os.path.join(settings.MEDIA_ROOT, 'test_media')
    TEST_MEDIA_URL = os.path.join(settings.MEDIA_URL, 'test_media/')


    def before(self):
        from django.conf import settings
        settings.DEFAULT_FILE_STORAGE = 'nosedjango.nosedjango.TestFileSystemStorage'

    def after(self):
        self.clear_test_media()

    def clear_test_media(self):
        try:
            shutil.rmtree(SetupTestFilesystem.TEST_MEDIA_ROOT)
        except OSError:
            pass


class SetupCeleryTesting():
    def before(self):
        from django.conf import settings
        settings.CELERY_ALWAYS_EAGER = True

    def after(self):
        pass

class SetupCacheTesting():
    def before(self):
        from django.conf import settings
        settings.CACHE_BACKEND = 'locmem://'

    def after(self):
        pass


# Next 3 plugins taken from django-sane-testing: http://github.com/Almad/django-sane-testing
# By: Lukas "Almad" Linhart http://almad.net/
#####
### It was a nice try with Django server being threaded.
### It still sucks for some cases (did I mentioned urllib2?),
### so provide cherrypy as working alternative.
### Do imports in method to avoid CP as dependency
### Code originally written by Mikeal Rogers under Apache License.
#####

class CherryPyLiveServerPlugin(Plugin):
    name = 'cherrypyliveserver'
    activation_parameter = '--with-cherrypyliveserver'

    def __init__(self):
        Plugin.__init__(self)
        self.server_started = False
        self.server_thread = None

    def options(self, parser, env=os.environ):
        Plugin.options(self, parser, env)

    def configure(self, options, config):
        Plugin.configure(self, options, config)

    def startTest(self, test):
        from django.conf import settings

        if not self.server_started and \
           getattr(test, 'start_live_server', False):

            self.start_server(
                address=getattr(settings, "LIVE_SERVER_ADDRESS", DEFAULT_LIVE_SERVER_ADDRESS),
                port=int(getattr(settings, "LIVE_SERVER_PORT", DEFAULT_LIVE_SERVER_PORT))
            )
            self.server_started = True

    def finalize(self, result):
        self.stop_test_server()

    def start_server(self, address='0.0.0.0', port=8000):
        _application = AdminMediaHandler(WSGIHandler())

        def application(environ, start_response):
            environ['PATH_INFO'] = environ['SCRIPT_NAME'] + environ['PATH_INFO']
            return _application(environ, start_response)

        from cherrypy.wsgiserver import CherryPyWSGIServer
        from threading import Thread
        self.httpd = CherryPyWSGIServer((address, port), application, server_name='django-test-http')
        self.httpd_thread = Thread(target=self.httpd.start)
        self.httpd_thread.start()
        #FIXME: This could be avoided by passing self to thread class starting django
        # and waiting for Event lock
        sleep(.5)

    def stop_test_server(self):
        if self.server_started:
            self.httpd.stop()
            self.server_started = False