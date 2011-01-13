from django.conf import settings as django_settings

from compressor.conf import settings
from compressor.base import Compressor, UncompressableFileError

class CssCompressor(Compressor):

    def __init__(self, content, output_prefix="css"):
        super(CssCompressor, self).__init__(content, output_prefix)
        self.extension = ".css"
        self.template_name = "compressor/css.html"
        self.template_name_inline = "compressor/css_inline.html"
        self.filters = list(settings.COMPRESS_CSS_FILTERS)
        self.type = 'css'

    def split_contents(self):
        if self.split_content:
            return self.split_content
        self.media_nodes = []
        for elem in self.parser.css_elems():
            data = None
            elem_name = self.parser.elem_name(elem)
            elem_attribs = self.parser.elem_attribs(elem)
            if elem_name == 'link' and elem_attribs['rel'] == 'stylesheet':
                try:
                    content = self.parser.elem_content(elem)
                    data = ('file', self.get_filename(elem_attribs['href']), elem)
                except UncompressableFileError:
                    if django_settings.DEBUG:
                        raise
            elif elem_name == 'style':
                data = ('hunk', self.parser.elem_content(elem), elem)
            if data:
                self.split_content.append(data)
                media = elem_attribs.get('media', None)
                # Append to the previous node if it had the same media type,
                # otherwise create a new node.
                if self.media_nodes and self.media_nodes[-1][0] == media:
                    self.media_nodes[-1][1].split_content.append(data)
                else:
                    node = CssCompressor(content='')
                    node.split_content.append(data)
                    self.media_nodes.append((media, node))
        return self.split_content

    def output(self):
        self.split_contents()
        if not hasattr(self, 'media_nodes'):
            return super(CssCompressor, self).output()
        if not settings.COMPRESS:
            return self.content
        ret = []
        for media, subnode in self.media_nodes:
            subnode.extra_context = {'media': media}
            ret.append(subnode.output())
        return ''.join(ret)
