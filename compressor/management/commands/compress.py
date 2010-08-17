from django.core.management.base import  NoArgsCommand, CommandError
from django.template.loader import find_template_loader
from compressor.conf import settings
import os
from fnmatch import fnmatch
from django.template import Template, TemplateSyntaxError
from django.conf import settings as django_settings
from compressor.templatetags.compress import CompressorNode
from django.template.context import Context
from django.utils.simplejson.decoder import JSONDecoder
from optparse import make_option

__author__ = 'ulo'

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('-c', '--context', default="", dest='context',
            help="""Context to use while rendering the 'compress' nodes."""
                """ (In JSON format; e.g.: '{"something": 1, "other": "value"}'"""),
    )

    def handle_noargs(self, **options):
        paths = []
        for loader in settings.TEMPLATE_LOADERS:
            loader_class = find_template_loader(loader)

            # We need new-style template loaders
            if hasattr(loader_class, "get_template_sources"):
                paths.extend(loader_class.get_template_sources(''))

        if not paths:
            raise CommandError("No template paths found. You need to configure settings.TEMPLATE_LOADERS.")

        template_files = []
        for path in paths:
            for root, dirs, files in os.walk(path):
                template_files.extend(os.path.join(root, name) for name in files if any(fnmatch(name, glob) for glob in settings.TEMPLATE_GLOB))

        if not template_files:
            raise CommandError("No templates found. You need to configure settings.TEMPLATE_LOADERS.")

        compressor_nodes = []
        for template_filename in template_files:
            try:
                template_file = open(template_filename)
                try:
                    template = Template(template_file.read().decode(django_settings.FILE_CHARSET))
                finally:
                    template_file.close()
            except IOError: # unreadable file -> ignore
                continue
            except TemplateSyntaxError: # broken template -> ignore
                continue

            compressor_nodes.extend(self.walk_nodes(template))

        if not compressor_nodes:
            raise CommandError("No 'compress' template tags found in templates.")

        optional_context = {}
        if "context" in options and options['context']:
            try:
                optional_context = JSONDecoder().decode(options['context'])
            except ValueError, e:
                raise CommandError("Invalid context JSON specified.", e)
        for node in compressor_nodes:
            result = node.render(Context(optional_context))
            print result

    def walk_nodes(self, start_node):
        compressor_nodes = []
        for node in getattr(start_node, "nodelist", []):
            if isinstance(node, CompressorNode):
                compressor_nodes.append(node)
            else:
                compressor_nodes.extend(self.walk_nodes(node))
        return compressor_nodes
