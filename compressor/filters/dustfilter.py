# -*- coding: utf-8 -*-

from compressor.conf import settings
from compressor.filters import CompilerFilter


class DustFilter(CompilerFilter):
    """
    Filter for dust templates.
    
    Precompiles templates with dustc (https://github.com/linkedin/dustjs/).
    Usage:
    {% compress js %}
    <script type="text/dust-template" charset="utf-8" src="/path/to/template.html" data-template-name="namespace/test">
    {% endcompress %}
    
    Add the following setting to COMPRESS_PRECOMPILERS:
    COMPRESS_PRECOMPILERS = (
        ...,
        ('text/dust-template', 'compressor.filters.dustfilter.DustFilter'),
    )
    """
    command = "{binary} {args} {infile}"
    type = 'file'
    options = (
        ('binary', 'dustc'),
    )

    class TemplateNameError(Exception):
        """ Raised when a dust template is included without the data-template-name attribute. """
    def __init__(self, content, attrs, *args, **kwargs):
        try:
            template_name = attrs['data-template-name']
            self.options += ('args', '--name=%s' % template_name),
        except:
            raise self.TemplateNameError
        super(DustFilter, self).__init__(content, *args, **kwargs)
