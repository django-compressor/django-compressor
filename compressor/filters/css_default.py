import os
import re

from compressor.filters import FilterBase, FilterError
from compressor.conf import settings

class CssAbsoluteFilter(FilterBase):
    def input(self, filename=None, **kwargs):
        if not filename or not filename.startswith(settings.MEDIA_ROOT):
            return self.content
        self.media_path = filename[len(settings.MEDIA_ROOT):]
        self.media_path = self.media_path.lstrip('/')
        self.media_url = settings.MEDIA_URL.rstrip('/')
        self.has_http = False
        if self.media_url.startswith('http://'):
            self.has_http = True
            self.media_url = self.media_url[7:]
        self.directory_name = '/'.join([self.media_url, os.path.dirname(self.media_path)])
        url_pattern = re.compile(r'url\(([^\)]+)\)')
        output = url_pattern.sub(self.url_converter, self.content)
        return output

    def url_converter(self, matchobj):
        url = matchobj.group(1)
        url = url.strip(' \'"')
        if url.startswith('http://') or url.startswith('/'):
            return "url('%s')" % url
        full_url = '/'.join([self.directory_name, url])
        full_url = os.path.normpath(full_url)
        if self.has_http:
            full_url = "http://%s" % full_url
        return "url('%s')" % full_url


class CssMediaFilter(FilterBase):
    def input(self, elem=None, **kwargs):
        try:
            self.media = elem['media']
        except (TypeError, KeyError):
            return self.content
        return "@media %s {%s}" % (self.media, self.content)
