from compressor.conf import settings
from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE
from compressor.exceptions import UncompressableFileError


class CssCompressor(Compressor):
    template_name = "compressor/css.html"
    template_name_inline = "compressor/css_inline.html"

    def __init__(self, content=None, output_prefix="css"):
        super(CssCompressor, self).__init__(content, output_prefix)
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
                    basename = self.get_basename(elem_attribs['href'])
                    filename = self.get_filename(basename)
                    data = (SOURCE_FILE, filename, basename, elem)
                except UncompressableFileError:
                    if settings.DEBUG:
                        raise
            elif elem_name == 'style':
                data = (SOURCE_HUNK, self.parser.elem_content(elem), None, elem)
            if data:
                self.split_content.append(data)
                media = elem_attribs.get('media', None)
                # Append to the previous node if it had the same media type,
                # otherwise create a new node.
                if self.media_nodes and self.media_nodes[-1][0] == media:
                    self.media_nodes[-1][1].split_content.append(data)
                else:
                    node = CssCompressor(str(elem))
                    node.split_content.append(data)
                    self.media_nodes.append((media, node))
        return self.split_content

    def output(self, *args, **kwargs):
        # Populate self.split_content
        if (settings.COMPRESS_ENABLED or settings.COMPRESS_PRECOMPILERS or
                kwargs.get('forced', False)):
            self.split_contents()
            if hasattr(self, 'media_nodes'):
                ret = []
                for media, subnode in self.media_nodes:
                    subnode.extra_context.update({'media': media})
                    ret.append(subnode.output(*args, **kwargs))
                return ''.join(ret)
        return super(CssCompressor, self).output(*args, **kwargs)
