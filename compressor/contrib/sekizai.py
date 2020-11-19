"""
 source: https://gist.github.com/1311010
 Get django-sekizai, django-compessor (and django-cms) playing nicely together
 re: https://github.com/ojii/django-sekizai/issues/4
 using: https://github.com/django-compressor/django-compressor.git
 and: https://github.com/ojii/django-sekizai.git@0.6 or later
"""
from compressor.templatetags.compress import CompressorNode
from compressor.exceptions import UncompressableFileError
from compressor.base import Compressor
from compressor.conf import settings
from compressor.utils import get_class

from django.template.base import TextNode
import re


def compress(context, data, name):
    """
    Data is the string from the template (the list of js files in this case)
    Name is either 'js' or 'css' (the sekizai namespace)
    Basically passes the string through the {% compress 'js' %} template tag
    Alternatively, if the block can contain a html comment structured like:
    <!-- compress_options [params] -->
    params can be: one of ['js','css'] and one or multiple of ['file','preload','inline','defer']
    """
    # separate compressible from uncompressable files
    options = []
    kind = name
    m = re.search('<!-- *compress_options *([a-z ]+?) *-->', data)
    if m is not None:
        options_clean = re.sub(' +', ' ', m.groups()[0])
        options = set(options_clean.split(' '))
        if 'js' in options and 'css' not in options:
            kind = 'js'
        elif 'css' in options and 'js' not in options:
            kind = 'css'

    parser = get_class(settings.COMPRESS_PARSER)(data)
    js_compressor, css_compressor = Compressor('js'), Compressor('css')
    compressable_elements, expanded_elements, deferred_elements = [], [], []
    if kind == 'js':
        for elem in parser.js_elems():
            attribs = parser.elem_attribs(elem)
            try:
                if 'src' in attribs:
                    js_compressor.get_basename(attribs['src'])
            except UncompressableFileError:
                if 'defer' in attribs:
                    deferred_elements.append(elem)
                else:
                    expanded_elements.append(elem)
            else:
                compressable_elements.append(elem)
    elif kind == 'css':
        for elem in parser.css_elems():
            attribs = parser.elem_attribs(elem)
            try:
                if parser.elem_name(elem) == 'link' and attribs['rel'].lower() == 'stylesheet':
                    css_compressor.get_basename(attribs['href'])
            except UncompressableFileError:
                expanded_elements.append(elem)
            else:
                compressable_elements.append(elem)

    # reconcatenate them
    results = []
    data = ''.join(parser.elem_str(e) for e in expanded_elements)
    expanded_node = CompressorNode(nodelist=TextNode(data), kind=kind, mode='file')
    results.append(expanded_node.get_original_content(context=context))

    if 'file' in options or len(options) == 0:
        data = ''.join(parser.elem_str(e) for e in compressable_elements)
        compressable_node = CompressorNode(nodelist=TextNode(data), kind=kind, mode='file')
        tmp_result = compressable_node.render(context=context)
        if 'defer' in options:
            tmp_result = re.sub("></script>$", " defer=\"defer\"></script>", tmp_result)
        results.append(tmp_result)

    if 'preload' in options:
        data = ''.join(parser.elem_str(e) for e in compressable_elements)
        compressable_node = CompressorNode(nodelist=TextNode(data), kind=kind, mode='preload')
        results.append(compressable_node.render(context=context))

    if 'inline' in options:
        data = ''.join(parser.elem_str(e) for e in compressable_elements)
        compressable_node = CompressorNode(nodelist=TextNode(data), kind=kind, mode='inline')
        results.append(compressable_node.render(context=context))

    data = ''.join(parser.elem_str(e) for e in deferred_elements)
    deferred_node = CompressorNode(nodelist=TextNode(data), kind=kind, mode='file')
    results.append(deferred_node.get_original_content(context=context))

    return '\n'.join(results)
