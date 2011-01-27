import os
import sys
import warnings

from django.core.management.base import  NoArgsCommand, CommandError
from django.template.loader import find_template_loader
from compressor.conf import settings
from fnmatch import fnmatch
from django.template import Template, TemplateSyntaxError
from django.conf import settings as django_settings
from compressor.templatetags.compress import CompressorNode
from django.template.context import Context
from django.utils.simplejson.decoder import JSONDecoder
from optparse import make_option
from django.core.cache import cache
from compressor.utils import make_offline_cache_key


class Command(NoArgsCommand):
    """Management command to offline generate the django_compressor cache content."""

    option_list = NoArgsCommand.option_list + (
        make_option('-c', '--context', default="", dest='context',
            help="""Context to use while rendering the 'compress' nodes."""
                 """ (In JSON format; e.g.: '{"something": 1, "other": "value"}'"""),
        make_option('-f', '--force', default=False, action="store_true", dest='force',
            help="Force generation of offline cache even if "
                 "settings.COMPRESS and/or settings.COMPRESS_OFFLINE is not set."),
    )

    def handle_noargs(self, **options):
        verbosity = int(options.get("verbosity", 0))

        if not settings.COMPRESS and not options.get("force"):
            raise CommandError(
                "Compressor is disabled. Set COMPRESS settting to True "
                "(or DEBUG to False) to enable. (Use -f to override)")

        if not settings.COMPRESS_OFFLINE:
            if not options.get("force"):
                raise CommandError(
                    "Aborting; COMPRESS_OFFLINE is not set. (Use -f to override)")
            warnings.warn(
                "COMPRESS_OFFLINE is not set. Offline generated cache will not be used.")

        if not settings.TEMPLATE_LOADERS:
            raise CommandError("No template loaders defined. You need to "
                               "configure TEMPLATE_LOADERS in your settings module.")

        paths = []
        for loader in settings.TEMPLATE_LOADERS:
            loader_class = find_template_loader(loader)

            # We need new-style class-based template loaders that have a
            # 'get_template_sources' method
            if hasattr(loader_class, "get_template_sources"):
                paths.extend(loader_class.get_template_sources(''))

        if not paths:
            raise CommandError(
                'No template paths found. None of the configured template '
                'loaders provided template paths. Offline compression needs '
                '"new-style" class-based template loaders. \n'
                'See: http://docs.djangoproject.com/en/dev/ref/settings/#template-loaders '
                'for more information on class-based loaders.')

        if verbosity > 1:
            sys.stdout.write("Considering paths:\n\t")
            sys.stdout.write("\n\t".join(paths))
            print
            
        template_files = []
        for path in paths:
            for root, dirs, files in os.walk(path):
                template_files.extend(
                    os.path.join(root, name) for name in files if any(
                        fnmatch(name, glob) for glob in settings.TEMPLATE_GLOB
                ))

        if not template_files:
            raise CommandError(
                "No templates found. You need to configure settings.TEMPLATE_LOADERS.")

        if verbosity > 1:
            sys.stdout.write("Found templates:\n\t")
            sys.stdout.write("\n\t".join(template_files))
            print

        compressor_nodes = {}
        for template_filename in template_files:
            try:
                template_file = open(template_filename)
                try:
                    template = Template(
                        template_file.read().decode(django_settings.FILE_CHARSET))
                finally:
                    template_file.close()
            except IOError: # unreadable file -> ignore
                if verbosity > 0:
                    print "Unreadable template at: %s" % template_filename
                continue
            except TemplateSyntaxError: # broken template -> ignore
                if verbosity > 0:
                    print "Invalid template at: %s" % template_filename
                continue

            nodes = self.walk_nodes(template)
            if nodes:
                compressor_nodes.setdefault(template_filename, []).extend(nodes)

        if not compressor_nodes:
            raise CommandError("No 'compress' template tags found in templates.")

        if verbosity > 0:
            sys.stdout.write("Found 'compress' tags in:\n\t")
            sys.stdout.write("\n\t".join(compressor_nodes.keys()))
            print

        context_content = {'_ignore_offline_setting': True}
        if "context" in options and options['context']:
            try:
                context_content.update(JSONDecoder().decode(options['context']))
            except ValueError, e:
                raise CommandError("Invalid context JSON specified.", e)


        sys.stdout.write("Compressing... ")
        count = 0
        for filename, nodes in compressor_nodes.items():
            for node in nodes:
                key = make_offline_cache_key(node.nodelist)
                result = node.render(Context(context_content))
                print result
                cache.set(key, result, settings.OFFLINE_TIMEOUT)
                count += 1
        sys.stdout.write("done\nCompressed %d block(s) from %d template(s)." %
                         (count, len(compressor_nodes)))

    def walk_nodes(self, start_node):
        compressor_nodes = []
        for node in getattr(start_node, "nodelist", []):
            if isinstance(node, CompressorNode):
                compressor_nodes.append(node)
            else:
                compressor_nodes.extend(self.walk_nodes(node))
        return compressor_nodes
