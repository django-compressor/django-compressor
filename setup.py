import os
from distutils.core import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

README = read('README.rst')

setup(
    name = "django_compressor",
    version = "0.5.2",
    url = 'http://github.com/mintchaos/django_compressor',
    license = 'BSD',
    description = "Compresses linked and inline javascript or CSS into a single cached file.",
    long_description = README,

    author = 'Christian Metts',
    author_email = 'xian@mintchaos.com',
    packages = [
        'compressor',
        'compressor.conf',
        'compressor.filters',
        'compressor.filters.jsmin',
        'compressor.templatetags',
    ],
    package_data = {
        'compressor': [
                'templates/compressor/*.html',
            ],
    },
    requires = [
        'BeautifulSoup',
    ],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
