Django Compressor
=================

Django Compressor can concatenate and then compress linked and inline Javascript
& CSS into cached single static files.

The compress template tag parses all the HTML in between `{% compress js/css %}`
and `{% endcompress %}` and looks for linked stylesheets or JS. It then
concatenates the files and inline styles/scripts and optionally compresses them
using one of the provided or a custom filter.

This process can also be started using the Django management command
`manage.py compress`.

The `in-development version`_ of django-compressor can be installed with
``pip install django_compressor==dev`` or ``easy_install django_compressor==dev``.

More
----

* More documentation about the usage and settings of django-compressor can be found
  at `readthedocs.org/docs/django_compressor/en/latest`_.

* The source code for django-compressor can be found and contributed to on
  `github.com/jezdez/django_compressor`_. There you can also file tickets.

.. _readthedocs.org/docs/django_compressor/en/latest: http://readthedocs.org/docs/django_compressor/en/latest
.. _github.com/jezdez/django_compressor: http://github.com/jezdez/django_compressor
.. _in-development version: http://github.com/jezdez/django_compressor/tarball/master#egg=django_compressor-dev
