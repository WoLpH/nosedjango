Nose django helper plugin
=========================

With this plugin you can write standard Nose unit tests inside a
Django application.

The plugin takes care of finding your applications settings.py file
and creating/tearing down test database. It also has support for
fixtures and it has experimental mechanism that wraps the tests in
transactions to speed up testing.

This plugin has been tested with Django 1.0-branch. It probably works
with 1.1.

Usage
-----

Unit tests can be run with following command::

  nose-django --with-django [nose-options]

Custom settings be used by setting ``DJANGO_SETTINGS_MODULE``
environmental variable.

Building Debian package
-----------------------

Plugin can also be installed as a Debian package::

  dpkg-checkbuilddeps
  dpkg-buildpackage -us -uc -rfakeroot
  sudo debi

Testing
-------

The `project` sample Django project was created using Django 1.0b1.

Using a more recent version of Django may cause problems.  You've been
warned.

If you change directory into the 'project' directory, you should be
able  to run the nose test runner and get reasonable results.

Note that you *won't* be running your doctests unless you tell nose to
do so.

As usual, you need to tell nose to run doctest test strings in modules
that contain standard test classes.

A successful run should hit *14* test cases excercising :

    * race conditions between test cases that create objects in test
      methods
    * race conditions between test cases that create objects in 
      fixture loading
    * doctests
    * test functions
    * mixes of doctests and test modules
    * docstrings in models

Transaction support
~~~~~~~~~~~~~~~~~~~

As default, nosedjango plugin runs the tests within a transaction.
This behaviour can be altered in two ways:

* Having ``DISABLE_TRANSACTION_MANAGEMENT`` in settings.py makes
  nosedjango not to use transactions

* Having ``use_transaction = False`` in test's context prevents using
  transaction for the test. Note: this can not override
  ``DISABLE_TRANSACTION_MANAGEMENT``. Example::

    use_transaction = False

    def test_simple():
       assert True

  Note, that this implies to *all* tests in the same context (ie.
  module or class)

Using fixtures
~~~~~~~~~~~~~~

Nosedjango supports loading fixtures from test's context. Fixtures are
generated the same way as they are in the traditional Django test
system: using ``manage.py dumpdata``. Example::

  fixtures = ['cheese.json', 'cakes']

  def test_cheesecake():
     # do something...

Note, that this implies to *all* tests in the same context (ie.
module or class)


Sample test run
~~~~~~~~~~~~~~~
::

  $ nosetests -v --with-django --with-doctest --doctest-tests --doctest-tests

  Doctest: project.zoo.models.Zoo ... ok
  Doctest: project.zoo.models.Zoo.__str__ ... ok
  Doctest: project.zoo.models.func ... ok
  This is just a stub for a regular test method ... ok
  Doctest: project.zoo.test_doctest_modules.test_docstring ... ok
  Doctest: project.zoo.test_doctest_modules.test_docstring ... ok
  project.zoo.test_fixtures.TestFixture1.test_count ... ok
  project.zoo.test_fixtures.TestFixture2.test_count ... ok
  project.zoo.test_race.TestDBRace1.test1 ... ok
  project.zoo.test_race.TestDBRace2.test1 ... ok
  We're customizing the ROOT_URLCONF with zoo.urls, ... ok
  We're using the standard ROOT_URLCONF, so we need to ... ok
  testcase1 (project.zoo.tests.TestDjango) ... ok
  testcase2 (project.zoo.tests.TestDjango) ... ok

  ----------------------------------------------------------------------
  Ran 14 tests in 1.219s

  OK
  Destroying test database...


Authors
-------

This version is maintained by Jyrki Pulliainen
<jyrki.pulliainen@inoi.fi>.

Original plugin courtesy of Victor Ng <crankycoder@gmail.com> who
rewrote Jason Pellerin's original nose-django plugin.

License
-------

This software is licensed with GNU LESSER GENERAL PUBLIC LICENSE
version 3 or (at your option) any later version. See `COPYING` for
more details.
