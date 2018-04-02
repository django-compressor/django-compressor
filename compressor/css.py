from compressor.base import Compressor, SOURCE_HUNK, SOURCE_FILE
from compressor.conf import settings


class CssCompressor(Compressor):

    output_mimetypes = {'text/css'}

    def split_contents(self):
        if self.split_content:
            return self.split_content
        self.media_nodes = []
        for elem in self.parser.css_elems():
            data = None
            elem_name = self.parser.elem_name(elem)
            elem_attribs = self.parser.elem_attribs(elem)
            if elem_name == 'link' and 'rel' in elem_attribs and elem_attribs['rel'].lower() == 'stylesheet':
                basename = self.get_basename(elem_attribs['href'])
                filename = self.get_filename(basename)
                data = (SOURCE_FILE, filename, basename, elem)
            elif elem_name == 'style':
                data = (SOURCE_HUNK, self.parser.elem_content(elem), None, elem)
            if data:
                self.split_content.append(data)
                media = elem_attribs.get('media', None)
                # Append to the previous node if it had the same media type
                append_to_previous = self.media_nodes and self.media_nodes[-1][0] == media
                # and we are not just precompiling, otherwise create a new node.
                if append_to_previous and settings.COMPRESS_ENABLED:
                    self.media_nodes[-1][1].split_content.append(data)
                else:
                    node = self.copy(content=self.parser.elem_str(elem))
                    node.split_content.append(data)
                    self.media_nodes.append((media, node))
        return self.split_content

    def output(self, *args, **kwargs):
        if (settings.COMPRESS_ENABLED or settings.COMPRESS_PRECOMPILERS or
                kwargs.get('forced', False)):
            # Populate self.split_content
            self.split_contents()
            if hasattr(self, 'media_nodes'):
                ret = []
                for media, subnode in self.media_nodes:
                    subnode.extra_context.update({'media': media})
                    ret.append(subnode.output(*args, **kwargs))
                return ''.join(ret)
        return super(CssCompressor, self).output(*args, **kwargs)
