import os
import re
import posixpath

from compressor.cache import get_hashed_mtime, get_hashed_content
from compressor.conf import settings
from compressor.filters import FilterBase, FilterError
from compressor.utils import staticfiles

URL_PATTERN = re.compile(r'url\(([^\)]+)\)')
SRC_PATTERN = re.compile(r'src=([\'"])(.+?)\1')
SCHEMES = ('http://', 'https://', '/', 'data:')


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
        if self.url.startswith(('http://', 'https://')):
            self.has_scheme = True
            parts = self.url.split('/')
            self.url = '/'.join(parts[2:])
            self.url_path = '/%s' % '/'.join(parts[3:])
            self.protocol = '%s/' % '/'.join(parts[:2])
            self.host = parts[2]
        self.directory_name = '/'.join((self.url, os.path.dirname(self.path)))
        return SRC_PATTERN.sub(self.src_converter,
            URL_PATTERN.sub(self.url_converter, self.content))

    def find(self, basename):
        if settings.DEBUG and basename and staticfiles.finders:
            return staticfiles.finders.find(basename)

    def guess_filename(self, url):
        local_path = url
        if self.has_scheme:
            # COMPRESS_URL had a protocol,
            # remove it and the hostname from our path.
            local_path = local_path.replace(self.protocol + self.host, "", 1)
        # Now, we just need to check if we can find
        # the path from COMPRESS_URL in our url
        if local_path.startswith(self.url_path):
            local_path = local_path.replace(self.url_path, "", 1)
        # Re-build the local full path by adding root
        filename = os.path.join(self.root, local_path.lstrip('/'))
        return os.path.exists(filename) and filename

    def add_suffix(self, url):
        filename = self.guess_filename(url)
        suffix = None
        if filename:
            if settings.COMPRESS_CSS_HASHING_METHOD == "mtime":
                suffix = get_hashed_mtime(filename)
            elif settings.COMPRESS_CSS_HASHING_METHOD in ("hash", "content"):
                suffix = get_hashed_content(filename)
            else:
                raise FilterError('COMPRESS_CSS_HASHING_METHOD is configured '
                                  'with an unknown method (%s).' %
                                  settings.COMPRESS_CSS_HASHING_METHOD)
        if suffix is None:
            return url
        if url.startswith(SCHEMES):
            if "?" in url:
                url = "%s&%s" % (url, suffix)
            else:
                url = "%s?%s" % (url, suffix)
        return url

    def _converter(self, matchobj, group, template):
        url = matchobj.group(group)
        url = url.strip(' \'"')
        if url.startswith(SCHEMES):
            return "url('%s')" % self.add_suffix(url)
        full_url = posixpath.normpath('/'.join([str(self.directory_name),
                                                url]))
        if self.has_scheme:
            full_url = "%s%s" % (self.protocol, full_url)
        return template % self.add_suffix(full_url)

    def url_converter(self, matchobj):
        return self._converter(matchobj, 1, "url('%s')")

    def src_converter(self, matchobj):
        return self._converter(matchobj, 2, "src='%s'")
