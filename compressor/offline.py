import os
from compressor.conf import settings
from fnmatch import fnmatch
from django.template.loader import find_template_loader
from django.template import Template, TemplateSyntaxError
from django.conf import settings as django_settings
from compressor.exceptions import OfflineGenerationError
from compressor.templatetags.compress import CompressorNode
from django.template.context import Context
from django.core.cache import cache
from compressor.utils import make_offline_cache_key
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

def _walk_nodes(start_node):
    compressor_nodes = []
    for node in getattr(start_node, "nodelist", []):
        if isinstance(node, CompressorNode):
            compressor_nodes.append(node)
        else:
            compressor_nodes.extend(_walk_nodes(node))
    return compressor_nodes


def compress_offline(verbosity=0, context=None, log=None):
    """
    Searches templates containing 'compress' nodes and compresses them "offline".
    The result is cached with a cache-key derived from the content of the compress
    nodes (not the content of the possibly linked files!).
    """
    if not log:
        log = StringIO()
    if not settings.TEMPLATE_LOADERS:
        raise OfflineGenerationError(
            "No template loaders defined. You need to configure "
            "TEMPLATE_LOADERS in your settings module.")

    paths = set()
    for loader in settings.TEMPLATE_LOADERS:
        loader_class = find_template_loader(loader)

        # We need new-style class-based template loaders that have a
        # 'get_template_sources' method
        if hasattr(loader_class, "get_template_sources"):
            paths.update(loader_class.get_template_sources(''))

    if not paths:
        raise OfflineGenerationError(
            'No template paths found. None of the configured template '
            'loaders provided template paths. Offline compression needs '
            '"new-style" class-based template loaders. \n'
            'See: http://docs.djangoproject.com/en/dev/ref/settings/#template-loaders '
            'for more information on class-based loaders.')

    if verbosity > 1:
        log.write("Considering paths:\n\t")
        log.write("\n\t".join(paths))
        print

    template_files = set()
    for path in paths:
        for root, dirs, files in os.walk(path):
            template_files.update(
                os.path.join(root, name) for name in files if any(
                    fnmatch(name, glob) for glob in settings.TEMPLATE_GLOB
            ))

    if not template_files:
        raise OfflineGenerationError(
            "No templates found. Make sure your TEMPLATE_LOADERS and "
            "TEMPLATE_DIRS settings are correct.")

    if verbosity > 1:
        log.write("Found templates:\n\t")
        log.write("\n\t".join(template_files))
        log.write("\n")

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
                log.write("Unreadable template at: %s\n" % (template_filename, ))
            continue
        except TemplateSyntaxError: # broken template -> ignore
            if verbosity > 0:
                log.write("Invalid template at: %s\n" % (template_filename, ))
            continue
        except UnicodeDecodeError, e:
            if verbosity > 0:
                log.write(
                    "UnicodeDecodeError while trying to read template at: %s\n" %
                    (template_filename, ))

        nodes = _walk_nodes(template)
        if nodes:
            compressor_nodes.setdefault(template_filename, []).extend(nodes)

    if not compressor_nodes:
        raise OfflineGenerationError(
            "No 'compress' template tags found in templates.")

    if verbosity > 0:
        log.write("Found 'compress' tags in:\n\t")
        log.write("\n\t".join(compressor_nodes.keys()))
        log.write("\n")

    context_content = context or {}

    # enable compression for render() calls below
    settings.COMPRESS = True
    settings.COMPRESS_OFFLINE = False

    log.write("Compressing... ")
    count = 0
    results = []
    for filename, nodes in compressor_nodes.items():
        for node in nodes:
            key = make_offline_cache_key(node.nodelist)
            result = node.render(Context(context_content))
            cache.set(key, result, settings.OFFLINE_TIMEOUT)
            results.append(result)
            count += 1
    log.write("done\nCompressed %d block(s) from %d template(s)." %
                     (count, len(compressor_nodes)))
    return count, results
