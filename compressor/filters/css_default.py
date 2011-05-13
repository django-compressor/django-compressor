import os
import re
import posixpath

from compressor.cache import get_hashed_mtime
from compressor.conf import settings
from compressor.filters import FilterBase
from compressor.utils import staticfiles

URL_PATTERN = re.compile(r'url\(([^\)]+)\)')


class CssAbsoluteFilter(FilterBase):

    def __init__(self, *args, **kwargs):
        super(CssAbsoluteFilter, self).__init__(*args, **kwargs)
        self.root = settings.COMPRESS_ROOT
        self.url = settings.COMPRESS_URL.rstrip('/')
        self.url_path = self.url
        self.has_scheme = False

    def input(self, filename=None, basename=None, **kwargs):
        if filename is not None:
            filename = os.path.normcase(os.path.abspath(filename))
        if (not (filename and filename.startswith(self.root)) and
                not self.find(basename)):
            return self.content
        self.path = basename.replace(os.sep, '/')
        self.path = self.path.lstrip('/')
        self.mtime = get_hashed_mtime(filename)
        if self.url.startswith(('http://', 'https://')):
            self.has_scheme = True
            parts = self.url.split('/')
            self.url = '/'.join(parts[2:])
            self.url_path = '/%s' % '/'.join(parts[3:])
            self.protocol = '%s/' % '/'.join(parts[:2])
            self.host = parts[2]
        self.directory_name = '/'.join((self.url, os.path.dirname(self.path)))
        return URL_PATTERN.sub(self.url_converter, self.content)

    def find(self, basename):
        if settings.DEBUG and basename and staticfiles.finders:
            return staticfiles.finders.find(basename)

    def guess_filename(self, url):
        local_path = url
        if self.has_scheme:
            # COMPRESS_URL had a protocol, remove it and the hostname from our path.
            local_path = local_path.replace(self.protocol + self.host, "", 1)
        # Now, we just need to check if we can find the path from COMPRESS_URL in our url
        if local_path.startswith(self.url_path):
            local_path = local_path.replace(self.url_path, "", 1)
        # Re-build the local full path by adding root
        filename = os.path.join(self.root, local_path.lstrip(os.sep))
        return os.path.exists(filename) and filename

    def add_mtime(self, url):
        filename = self.guess_filename(url)
        mtime = filename and get_hashed_mtime(filename) or self.mtime
        if mtime is None:
            return url
        if url.startswith(('http://', 'https://', '/')):
            if "?" in url:
                url = "%s&%s" % (url, mtime)
            else:
                url = "%s?%s" % (url, mtime)
        return url

    def url_converter(self, matchobj):
        url = matchobj.group(1)
        url = url.strip(' \'"')
        if url.startswith(('http://', 'https://', '/', 'data:')):
            return "url('%s')" % self.add_mtime(url)
        full_url = posixpath.normpath('/'.join([self.directory_name, url]))
        if self.has_scheme:
            full_url = "%s%s" % (self.protocol, full_url)
        return "url('%s')" % self.add_mtime(full_url)
