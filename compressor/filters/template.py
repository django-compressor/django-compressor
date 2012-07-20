from django.template import Template, Context
from django.conf import settings

from compressor.filters import FilterBase


class TemplateFilter(FilterBase):

    def input(self, filename=None, basename=None, **kwargs):
        template = Template(self.content)
        context = Context(settings.COMPRESS_TEMPLATE_FILTER_CONTEXT)
        return template.render(context)
