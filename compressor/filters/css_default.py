import os
import re
import posixpath

from compressor.filters import FilterBase, FilterError
from compressor.conf import settings
from compressor.utils import get_hexdigest, get_mtime

URL_PATTERN = re.compile(r'url\(([^\)]+)\)')


class CssAbsoluteFilter(FilterBase):
    def input(self, filename=None, **kwargs):
        media_root = os.path.normcase(os.path.abspath(settings.MEDIA_ROOT))
        if filename is not None:
            filename = os.path.normcase(os.path.abspath(filename))
        if not filename or not filename.startswith(media_root):
            return self.content
        self.media_path = filename[len(media_root):].replace(os.sep, '/')
        self.media_path = self.media_path.lstrip('/')
        self.media_url = settings.MEDIA_URL.rstrip('/')
        try:
            mtime = get_mtime(filename)
            self.mtime = get_hexdigest(str(int(mtime)))[:12]
        except OSError:
            self.mtime = None
        self.has_http = False
        if self.media_url.startswith('http://') or self.media_url.startswith('https://'):
            self.has_http = True
            parts = self.media_url.split('/')
            self.media_url = '/'.join(parts[2:])
            self.protocol = '%s/' % '/'.join(parts[:2])
        self.directory_name = '/'.join([self.media_url, os.path.dirname(self.media_path)])
        output = URL_PATTERN.sub(self.url_converter, self.content)
        return output

    def add_mtime(self, url):
        if self.mtime is None:
            return url
        if (url.startswith('http://') or
            url.startswith('https://') or
            url.startswith('/')):
            if "?" in url:
                return "%s&%s" % (url, self.mtime)
            return "%s?%s" % (url, self.mtime)
        return url

    def url_converter(self, matchobj):
        url = matchobj.group(1)
        url = url.strip(' \'"')
        if (url.startswith('http://') or
            url.startswith('https://') or
            url.startswith('/') or
            url.startswith('data:')):
            return "url('%s')" % self.add_mtime(url)
        full_url = '/'.join([str(self.directory_name), url])
        full_url = posixpath.normpath(full_url)
        if self.has_http:
            full_url = "%s%s" % (self.protocol, full_url)
        return "url('%s')" % self.add_mtime(full_url)
