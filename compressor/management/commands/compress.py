# flake8: noqa
import os
import sys

from collections import OrderedDict
from fnmatch import fnmatch
from optparse import make_option
from importlib import import_module

import django
from django.core.management.base import BaseCommand, CommandError
import django.template
from django.template import Context
from django.utils import six
from django.template.loader import get_template  # noqa Leave this in to preload template locations
from django.template.utils import InvalidTemplateEngineError
from django.template import engines

from compressor.cache import get_offline_hexdigest, write_offline_manifest
from compressor.conf import settings
from compressor.exceptions import (OfflineGenerationError, TemplateSyntaxError,
                                   TemplateDoesNotExist)
from compressor.templatetags.compress import CompressorNode
from compressor.utils import get_mod_func

if six.PY3:
    # there is an 'io' module in python 2.6+, but io.StringIO does not
    # accept regular strings, just unicode objects
    from io import StringIO
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


class Command(BaseCommand):
    help = "Compress content outside of the request/response cycle"
    option_list = BaseCommand.option_list + (
        make_option('--extension', '-e', action='append', dest='extensions',
            help='The file extension(s) to examine (default: ".html", '
                'separate multiple extensions with commas, or use -e '
                'multiple times)'),
        make_option('-f', '--force', default=False, action='store_true',
            help="Force the generation of compressed content even if the "
                "COMPRESS_ENABLED setting is not True.", dest='force'),
        make_option('--follow-links', default=False, action='store_true',
            help="Follow symlinks when traversing the COMPRESS_ROOT "
                "(which defaults to STATIC_ROOT). Be aware that using this "
                "can lead to infinite recursion if a link points to a parent "
                "directory of itself.", dest='follow_links'),
        make_option('--engine', default="django", action="store",
            help="Specifies the templating engine. jinja2 or django",
            dest="engine"),
    )

    def get_loaders(self):
        template_source_loaders = []
        for e in engines.all():
            if hasattr(e, 'engine'):
                template_source_loaders.extend(
                    e.engine.get_template_loaders(e.engine.loaders))
        loaders = []
        # If template loader is CachedTemplateLoader, return the loaders
        # that it wraps around. So if we have
        # TEMPLATE_LOADERS = (
        #    ('django.template.loaders.cached.Loader', (
        #        'django.template.loaders.filesystem.Loader',
        #        'django.template.loaders.app_directories.Loader',
        #    )),
        # )
        # The loaders will return django.template.loaders.filesystem.Loader
        # and django.template.loaders.app_directories.Loader
        # The cached Loader and similar ones include a 'loaders' attribute
        # so we look for that.
        for loader in template_source_loaders:
            if hasattr(loader, 'loaders'):
                loaders.extend(loader.loaders)
            else:
                loaders.append(loader)
        return loaders

    def __get_parser(self, engine):
        if engine == "jinja2":
            from compressor.offline.jinja2 import Jinja2Parser
            env = settings.COMPRESS_JINJA2_GET_ENVIRONMENT()
            parser = Jinja2Parser(charset=settings.FILE_CHARSET, env=env)
        elif engine == "django":
            from compressor.offline.django import DjangoParser
            parser = DjangoParser(charset=settings.FILE_CHARSET)
        else:
            raise OfflineGenerationError("Invalid templating engine specified.")

        return parser

    def compress(self, log=None, **options):
        """
        Searches templates containing 'compress' nodes and compresses them
        "offline" -- outside of the request/response cycle.

        The result is cached with a cache-key derived from the content of the
        compress nodes (not the content of the possibly linked files!).
        """
        engine = options.get("engine", "django")
        extensions = options.get('extensions')
        extensions = self.handle_extensions(extensions or ['html'])
        verbosity = int(options.get("verbosity", 0))
        if not log:
            log = StringIO()
        if not settings.TEMPLATE_LOADERS:
            raise OfflineGenerationError("No template loaders defined. You "
                                         "must set TEMPLATE_LOADERS in your "
                                         "settings.")
        templates = set()
        if engine == 'django':
            paths = set()
            for loader in self.get_loaders():
                try:
                    module = import_module(loader.__module__)
                    get_template_sources = getattr(module,
                        'get_template_sources', None)
                    if get_template_sources is None:
                        get_template_sources = loader.get_template_sources
                    paths.update(str(origin) for origin in get_template_sources(''))
                except (ImportError, AttributeError, TypeError):
                    # Yeah, this didn't work out so well, let's move on
                    pass

            if not paths:
                raise OfflineGenerationError("No template paths found. None of "
                                             "the configured template loaders "
                                             "provided template paths. See "
                                             "https://docs.djangoproject.com/en/1.8/topics/templates/ "
                                             "for more information on template "
                                             "loaders.")
            if verbosity > 1:
                log.write("Considering paths:\n\t" + "\n\t".join(paths) + "\n")

            for path in paths:
                for root, dirs, files in os.walk(path,
                        followlinks=options.get('followlinks', False)):
                    templates.update(os.path.join(root, name)
                        for name in files if not name.startswith('.') and
                            any(fnmatch(name, "*%s" % glob) for glob in extensions))
        elif engine == 'jinja2' and django.VERSION >= (1, 8):
            env = settings.COMPRESS_JINJA2_GET_ENVIRONMENT()
            if env and hasattr(env, 'list_templates'):
                templates |= set([env.loader.get_source(env, template)[1] for template in
                            env.list_templates(filter_func=lambda _path:
                            os.path.splitext(_path)[-1] in extensions)])

        if not templates:
            raise OfflineGenerationError("No templates found. Make sure your "
                                         "TEMPLATE_LOADERS and TEMPLATE_DIRS "
                                         "settings are correct.")
        if verbosity > 1:
            log.write("Found templates:\n\t" + "\n\t".join(templates) + "\n")

        parser = self.__get_parser(engine)
        compressor_nodes = OrderedDict()
        for template_name in templates:
            try:
                template = parser.parse(template_name)
            except IOError:  # unreadable file -> ignore
                if verbosity > 0:
                    log.write("Unreadable template at: %s\n" % template_name)
                continue
            except TemplateSyntaxError as e:  # broken template -> ignore
                if verbosity > 0:
                    log.write("Invalid template %s: %s\n" % (template_name, e))
                continue
            except TemplateDoesNotExist:  # non existent template -> ignore
                if verbosity > 0:
                    log.write("Non-existent template at: %s\n" % template_name)
                continue
            except UnicodeDecodeError:
                if verbosity > 0:
                    log.write("UnicodeDecodeError while trying to read "
                              "template %s\n" % template_name)
            try:
                nodes = list(parser.walk_nodes(template))
            except (TemplateDoesNotExist, TemplateSyntaxError) as e:
                # Could be an error in some base template
                if verbosity > 0:
                    log.write("Error parsing template %s: %s\n" % (template_name, e))
                continue
            if nodes:
                template.template_name = template_name
                compressor_nodes.setdefault(template, []).extend(nodes)

        if not compressor_nodes:
            raise OfflineGenerationError(
                "No 'compress' template tags found in templates."
                "Try running compress command with --follow-links and/or"
                "--extension=EXTENSIONS")

        if verbosity > 0:
            log.write("Found 'compress' tags in:\n\t" +
                      "\n\t".join((t.template_name
                                   for t in compressor_nodes.keys())) + "\n")

        contexts = settings.COMPRESS_OFFLINE_CONTEXT
        if isinstance(contexts, six.string_types):
            try:
                module, function = get_mod_func(contexts)
                contexts = getattr(import_module(module), function)()
            except (AttributeError, ImportError, TypeError) as e:
                raise ImportError("Couldn't import offline context function %s: %s" %
                                  (settings.COMPRESS_OFFLINE_CONTEXT, e))
        elif not isinstance(contexts, (list, tuple)):
            contexts = [contexts]

        log.write("Compressing... ")
        block_count = context_count = 0
        results = []
        offline_manifest = OrderedDict()

        for context_dict in contexts:
            context_count += 1
            init_context = parser.get_init_context(context_dict)

            for template, nodes in compressor_nodes.items():
                context = Context(init_context)
                template._log = log
                template._log_verbosity = verbosity

                if not parser.process_template(template, context):
                    continue

                for node in nodes:
                    context.push()
                    parser.process_node(template, context, node)
                    rendered = parser.render_nodelist(template, context, node)
                    key = get_offline_hexdigest(rendered)

                    if key in offline_manifest:
                        continue

                    try:
                        result = parser.render_node(template, context, node)
                    except Exception as e:
                        raise CommandError("An error occurred during rendering %s: "
                                           "%s" % (template.template_name, e))
                    offline_manifest[key] = result
                    context.pop()
                    results.append(result)
                    block_count += 1

        write_offline_manifest(offline_manifest)

        log.write("done\nCompressed %d block(s) from %d template(s) for %d context(s).\n" %
                  (block_count, len(compressor_nodes), context_count))
        return block_count, results

    def handle_extensions(self, extensions=('html',)):
        """
        organizes multiple extensions that are separated with commas or
        passed by using --extension/-e multiple times.

        for example: running 'django-admin compress -e js,txt -e xhtml -a'
        would result in an extension list: ['.js', '.txt', '.xhtml']

        >>> handle_extensions(['.html', 'html,js,py,py,py,.py', 'py,.py'])
        ['.html', '.js']
        >>> handle_extensions(['.html, txt,.tpl'])
        ['.html', '.tpl', '.txt']
        """
        ext_list = []
        for ext in extensions:
            ext_list.extend(ext.replace(' ', '').split(','))
        for i, ext in enumerate(ext_list):
            if not ext.startswith('.'):
                ext_list[i] = '.%s' % ext_list[i]
        return set(ext_list)

    def handle(self, **options):
        if not settings.COMPRESS_ENABLED and not options.get("force"):
            raise CommandError(
                "Compressor is disabled. Set the COMPRESS_ENABLED "
                "setting or use --force to override.")
        if not settings.COMPRESS_OFFLINE:
            if not options.get("force"):
                raise CommandError(
                    "Offline compression is disabled. Set "
                    "COMPRESS_OFFLINE or use the --force to override.")
        self.compress(sys.stdout, **options)



Command.requires_system_checks = False
