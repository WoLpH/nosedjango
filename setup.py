from setuptools import setup, find_packages

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
    packages = find_packages(),
    zip_safe = False,
    include_package_data = True,
    entry_points = {
        'nose.plugins': [
            'django = nosedjango.nosedjango:NoseDjango',
            'cherrypyliveserver = nosedjango.plugins.cherrypy:CherryPyLiveServerPlugin',
            'djangofilestorage = nosedjango.plugins.file_storage:FileStoragePlugin',
            'selenium = nosedjango.nosedjango:SeleniumPlugin',
            'djangosphinx = nosedjango.nosedjango:DjangoSphinxPlugin',
            ]
        }
    )

