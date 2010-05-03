import os
import re
import posixpath

from compressor.filters import FilterBase, FilterError
from compressor.conf import settings

class CssAbsoluteFilter(FilterBase):
    def input(self, filename=None, **kwargs):
        media_root = os.path.abspath(settings.MEDIA_ROOT)
        if filename is not None:
            filename = os.path.abspath(filename)
        if not filename or not filename.startswith(media_root):
            return self.content
        self.media_path = filename[len(media_root):]
        self.media_path = self.media_path.lstrip('/')
        self.media_url = settings.MEDIA_URL.rstrip('/')
        self.has_http = False
        if self.media_url.startswith('http://') or self.media_url.startswith('https://'):
            self.has_http = True
            parts = self.media_url.split('/')
            self.media_url = '/'.join(parts[2:])
            self.protocol = '%s/' % '/'.join(parts[:2])
        self.directory_name = '/'.join([self.media_url, os.path.dirname(self.media_path)])
        url_pattern = re.compile(r'url\(([^\)]+)\)')
        output = url_pattern.sub(self.url_converter, self.content)
        return output

    def url_converter(self, matchobj):
        url = matchobj.group(1)
        url = url.strip(' \'"')
        if (url.startswith('http://') or 
            url.startswith('https://') or 
            url.startswith('/') or 
            url.startswith('data:')):
            return "url('%s')" % url
        full_url = '/'.join([str(self.directory_name), url])
        full_url = posixpath.normpath(full_url)
        if self.has_http:
            full_url = "%s%s" % (self.protocol,full_url)
        return "url('%s')" % full_url
