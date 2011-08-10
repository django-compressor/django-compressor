import os
import re
import mimetypes
from base64 import b64encode

from compressor.conf import settings
from compressor.filters import FilterBase


class DataUriFilter(FilterBase):
    """Filter for embedding media as data: URIs.

    Settings:
         COMPRESS_DATA_URI_MAX_SIZE: Only files that are smaller than this
                                     value will be embedded. Unit; bytes.


    Don't use this class directly. Use a subclass.
    """
    def input(self, filename=None, **kwargs):
        if not filename or not filename.startswith(settings.COMPRESS_ROOT):
            return self.content
        output = self.content
        for url_pattern in self.url_patterns:
            output = url_pattern.sub(self.data_uri_converter, output)
        return output

    def get_file_path(self, url):
        # strip query string of file paths
        if "?" in url:
            url = url.split("?")[0]
        return os.path.join(
            settings.COMPRESS_ROOT, url[len(settings.COMPRESS_URL):])

    def data_uri_converter(self, matchobj):
        url = matchobj.group(1).strip(' \'"')
        if not url.startswith('data:'):
            path = self.get_file_path(url)
            if os.stat(path).st_size <= settings.COMPRESS_DATA_URI_MAX_SIZE:
                data = b64encode(open(path, 'rb').read())
                return 'url("data:%s;base64,%s")' % (
                    mimetypes.guess_type(path)[0], data)
        return 'url("%s")' % url


class CssDataUriFilter(DataUriFilter):
    """Filter for embedding media as data: URIs in CSS files.

    See DataUriFilter.
    """
    url_patterns = (
        re.compile(r'url\(([^\)]+)\)'),
    )
