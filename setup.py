import os
from setuptools import setup, find_packages
from finddata import find_package_data

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

README = read('README.rst')

setup(
    name = "django_compressor",
    version = "0.6a8",
    url = 'http://github.com/jezdez/django_compressor',
    license = 'BSD',
    description = "Compresses linked and inline javascript or CSS into a single cached file.",
    long_description = README,
    author = 'Jannis Leidel',
    author_email = 'jannis@leidel.info',
    packages = find_packages(),
    package_data = find_package_data('compressor'),
    install_requires = [
        'BeautifulSoup',
    ],
    tests_require = [
        'Django', 'lxml', 'BeautifulSoup',
    ],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
    test_suite='compressor.tests.runtests.runtests',
    zip_safe = False,
)
