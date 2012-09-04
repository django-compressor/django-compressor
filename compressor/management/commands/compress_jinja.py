# flake8: noqa
import sys
import jinja2
from jinja2.nodes import CallBlock, Call, ExtensionAttribute
from types import MethodType
from optparse import make_option

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO  # noqa

from django.core.management.base import NoArgsCommand, CommandError
from coffin.template import (Context, Template)
from jinja2.exceptions import TemplateSyntaxError
from django.template import (TemplateDoesNotExist)
from django.utils.datastructures import SortedDict
from django.template.loader_tags import (ExtendsNode,
                                         BLOCK_CONTEXT_KEY)

try:
    from django.template.loaders.cached import Loader as CachedLoader
except ImportError:
    CachedLoader = None  # noqa

from compressor.cache import get_offline_hexdigest, write_offline_manifest
from compressor.conf import settings
from compressor.exceptions import OfflineGenerationError
from compressor.templatetags.compress import CompressorNode


def patched_render(self, context):
    # 'Fake' _render method that just returns the context instead of
    # rendering. It also checks whether the first node is an extend node or
    # not, to be able to handle complex inheritance chain.
    self._render_firstnode = MethodType(patched_render_firstnode, self)
    self._render_firstnode(context)

    # Cleanup, uninstall our _render monkeypatch now that it has been called
    self._render = self._old_render
    return context


def patched_render_firstnode(self, context):
    # If this template has a ExtendsNode, we want to find out what
    # should be put in render_context to make the {% block ... %}
    # tags work.
    #
    # We can't fully render the base template(s) (we don't have the
    # full context vars - only what's necessary to render the compress
    # nodes!), therefore we hack the ExtendsNode we found, patching
    # its get_parent method so that rendering the ExtendsNode only
    # gives us the blocks content without doing any actual rendering.
    extra_context = {}
    try:
        firstnode = self.nodelist[0]
    except IndexError:
        firstnode = None
    if isinstance(firstnode, ExtendsNode):
        firstnode._log = self._log
        firstnode._log_verbosity = self._log_verbosity
        firstnode._old_get_parent = firstnode.get_parent
        firstnode.get_parent = MethodType(patched_get_parent, firstnode)
        try:
            extra_context = firstnode.render(context)
            context.render_context = extra_context.render_context
            # We aren't rendering {% block %} tags, but we want
            # {{ block.super }} inside {% compress %} inside {% block %}s to
            # work. Therefore, we need to pop() the last block context for
            # each block name, to emulate what would have been done if the
            # {% block %} had been fully rendered.
            for blockname in firstnode.blocks.keys():
                context.render_context[BLOCK_CONTEXT_KEY].pop(blockname)
        except (IOError, TemplateSyntaxError, TemplateDoesNotExist):
            # That first node we are trying to render might cause more errors
            # that we didn't catch when simply creating a Template instance
            # above, so we need to catch that (and ignore it, just like above)
            # as well.
            if self._log_verbosity > 0:
                self._log.write("Caught error when rendering extend node from "
                                "template %s\n" % getattr(self, 'name', self))
            return None
        finally:
            # Cleanup, uninstall our get_parent monkeypatch now that it has
            # been called
            firstnode.get_parent = firstnode._old_get_parent
    return extra_context


def patched_get_parent(self, context):
    # Patch template returned by extendsnode's get_parent to make sure their
    # _render method is just returning the context instead of actually
    # rendering stuff.
    # In addition, this follows the inheritance chain by looking if the first
    # node of the template is an extend node itself.
    compiled_template = self._old_get_parent(context)
    compiled_template._log = self._log
    compiled_template._log_verbosity = self._log_verbosity
    compiled_template._old_render = compiled_template._render
    compiled_template._render = MethodType(patched_render, compiled_template)
    return compiled_template


class Command(NoArgsCommand):
    help = "Compress content outside of the request/response cycle"
    option_list = NoArgsCommand.option_list + (
        make_option('--extension', '-e', action='append', dest='extensions',
                    help='The file extension(s) to examine (default: ".html", '
                    'separate multiple extensions with commas, or use -e '
                    'multiple times)'),
        make_option('-f', '--force', default=False, action='store_true',
                    help="Force the generation of compressed content even if the "
                    "COMPRESS_ENABLED setting is not True.", dest='force'),
        make_option('--follow-links', default=False, action='store_true',
                    help="Follow symlinks when traversing the COMPRESS_ROOT "
                    "(which defaults to MEDIA_ROOT). Be aware that using this "
                    "can lead to infinite recursion if a link points to a parent "
                    "directory of itself.", dest='follow_links'),
    )

    requires_model_validation = False

    def get_loaders(self):
        from django.template.loader import template_source_loaders
        if template_source_loaders is None:
            try:
                from django.template.loader import (
                    find_template as finder_func)
            except ImportError:
                from django.template.loader import (
                    find_template_source as finder_func)  # noqa
            try:
                # Force django to calculate template_source_loaders from
                # TEMPLATE_LOADERS settings, by asking to find a dummy template
                source, name = finder_func('test')
            except TemplateDoesNotExist:
                pass
            # Reload template_source_loaders now that it has been calculated ;
            # it should contain the list of valid, instanciated template loaders
            # to use.
            from django.template.loader import template_source_loaders
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
        for loader in template_source_loaders:
            if CachedLoader is not None and isinstance(loader, CachedLoader):
                loaders.extend(loader.loaders)
            else:
                loaders.append(loader)
        return loaders

    def compress(self, log=None, **options):
        """
        Searches templates containing 'compress' nodes and compresses them
        "offline" -- outside of the request/response cycle.

        The result is cached with a cache-key derived from the content of the
        compress nodes (not the content of the possibly linked files!).
        """
        extensions = options.get('extensions')
        extensions = self.handle_extensions(extensions or ['html'])
        verbosity = int(options.get("verbosity", 0))
        if not log:
            log = StringIO()
        if not settings.TEMPLATE_LOADERS:
            raise OfflineGenerationError("No template loaders defined. You "
                                         "must set TEMPLATE_LOADERS in your "
                                         "settings.")
        from coffin.common import env
        templates = env.list_templates()

        if not templates:
            raise OfflineGenerationError("No templates found. Make sure your "
                                         "TEMPLATE_LOADERS and TEMPLATE_DIRS "
                                         "settings are correct.")
        if verbosity > 1:
            log.write("Found templates:\n\t" + "\n\t".join(templates) + "\n")

        compressor_nodes = SortedDict()
        for template_name in templates:
            try:
                template_content = env.loader.get_source(env, template_name)[0]
                template = env.parse(template_content)
            except IOError:  # unreadable file -> ignore
                if verbosity > 0:
                    log.write("Unreadable template at: %s\n" % template_name)
                continue
            except TemplateSyntaxError, e:  # broken template -> ignore
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
            nodes = list(self.walk_nodes(template))
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

        log.write("Compressing... ")
        count = 0
        results = []
        offline_manifest = SortedDict()
        for template, nodes in compressor_nodes.iteritems():
            context = Context(settings.COMPRESS_OFFLINE_CONTEXT)
            template._log = log
            template._log_verbosity = verbosity
            for node in nodes:
                context.push()
                compiled_node = env.compile(jinja2.nodes.Template(node.body))
                key = get_offline_hexdigest(Template.from_code(env, compiled_node, {}).render(context))
                try:
                    context['compress_forced'] = True
                    compiled_node = env.compile(jinja2.nodes.Template([node]))
                    result = Template.from_code(env, compiled_node, {}).render(context)
                except Exception, e:
                    raise CommandError("An error occured during rendering %s: "
                                       "%s" % (template.template_name, e))
                offline_manifest[key] = result
                context.pop()
                results.append(result)
                count += 1

        write_offline_manifest(offline_manifest)

        log.write("done\nCompressed %d block(s) from %d template(s).\n" %
                  (count, len(compressor_nodes)))
        return count, results

    def get_nodelist(self, node):
        if (isinstance(node, IfNode) and
                hasattr(node, 'nodelist_true') and
                hasattr(node, 'nodelist_false')):
            return node.nodelist_true + node.nodelist_false
        return getattr(node, "body", getattr(node, "nodes", []))

    def walk_nodes(self, node, block_name=None):
        for node in self.get_nodelist(node):
            if isinstance(node, CallBlock) and isinstance(node.call, Call) and isinstance(node.call.node, ExtensionAttribute)\
            and node.call.node.identifier == 'compressor.contrib.jinja2ext.CompressorExtension':
                yield node
            else:
                for node in self.walk_nodes(node, block_name=block_name):
                    yield node

    def handle_extensions(self, extensions=('html',)):
        """
        organizes multiple extensions that are separated with commas or
        passed by using --extension/-e multiple times.

        for example: running 'django-admin compress -e js,txt -e xhtml -a'
        would result in a extension list: ['.js', '.txt', '.xhtml']

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

    def handle_noargs(self, **options):
        if not settings.COMPRESS_ENABLED and not options.get("force"):
            raise CommandError(
                "Compressor is disabled. Set the COMPRESS_ENABLED "
                "settting or use --force to override.")
        if not settings.COMPRESS_OFFLINE:
            if not options.get("force"):
                raise CommandError(
                    "Offline compression is disabled. Set "
                    "COMPRESS_OFFLINE or use the --force to override.")
        self.compress(sys.stdout, **options)
