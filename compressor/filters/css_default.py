import os
import re
import posixpath

from compressor.cache import get_hashed_mtime, get_hashed_content
from compressor.conf import settings
from compressor.filters import FilterBase, FilterError

URL_PATTERN = re.compile(r"""
    url\(
    \s*      # any amount of whitespace
    ([\'"]?) # optional quote
    (.*?)    # any amount of anything, non-greedily (this is the actual url)
    \1       # matching quote (or nothing if there was none)
    \s*      # any amount of whitespace
    \)""", re.VERBOSE)
SRC_PATTERN = re.compile(r'src=([\'"])(.*?)\1')
SCHEMES = ('http://', 'https://', '/')


class CssAbsoluteFilter(FilterBase):

    run_with_compression_disabled = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = settings.COMPRESS_ROOT
        self.url = settings.COMPRESS_URL.rstrip('/')
        self.url_path = self.url
        self.has_scheme = False

    def input(self, filename=None, basename=None, **kwargs):
        if not filename:
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

    def guess_filename(self, url):
        local_path = url
        if self.has_scheme:
            # COMPRESS_URL had a protocol,
            # remove it and the hostname from our path.
            local_path = local_path.replace(self.protocol + self.host, "", 1)
        # remove url fragment, if any
        local_path = local_path.rsplit("#", 1)[0]
        # remove querystring, if any
        local_path = local_path.rsplit("?", 1)[0]
        # Now, we just need to check if we can find
        # the path from COMPRESS_URL in our url
        if local_path.startswith(self.url_path):
            local_path = local_path.replace(self.url_path, "", 1)
        # Re-build the local full path by adding root
        filename = os.path.join(self.root, local_path.lstrip('/'))
        return os.path.exists(filename) and filename

    def add_suffix(self, url):
        filename = self.guess_filename(url)
        if not filename:
            return url
        if settings.COMPRESS_CSS_HASHING_METHOD is None:
            return url
        if not url.startswith(SCHEMES):
            return url

        suffix = None
        if settings.COMPRESS_CSS_HASHING_METHOD == "mtime":
            suffix = get_hashed_mtime(filename)
        elif settings.COMPRESS_CSS_HASHING_METHOD in ("hash", "content"):
            suffix = get_hashed_content(filename)
        else:
            raise FilterError('COMPRESS_CSS_HASHING_METHOD is configured '
                              'with an unknown method (%s).' %
                              settings.COMPRESS_CSS_HASHING_METHOD)
        fragment = None
        if "#" in url:
            url, fragment = url.rsplit("#", 1)
        if "?" in url:
            url = "%s&%s" % (url, suffix)
        else:
            url = "%s?%s" % (url, suffix)
        if fragment is not None:
            url = "%s#%s" % (url, fragment)
        return url

    def _converter(self, url):
        if url.startswith(('#', 'data:')):
            return url
        elif url.startswith(SCHEMES):
            return self.add_suffix(url)
        full_url = posixpath.normpath('/'.join([str(self.directory_name),
                                                url]))
        if self.has_scheme:
            full_url = "%s%s" % (self.protocol, full_url)
        full_url = self.add_suffix(full_url)
        return self.post_process_url(full_url)

    def post_process_url(self, url):
        """
        Extra URL processing, to be overridden in subclasses.
        """
        return url

    def url_converter(self, matchobj):
        quote = matchobj.group(1)
        converted_url = self._converter(matchobj.group(2))
        return "url(%s%s%s)" % (quote, converted_url, quote)

    def src_converter(self, matchobj):
        quote = matchobj.group(1)
        converted_url = self._converter(matchobj.group(2))
        return "src=%s%s%s" % (quote, converted_url, quote)


class CssRelativeFilter(CssAbsoluteFilter):
    """
    Do similar to ``CssAbsoluteFilter`` URL processing
    but add a *relative URL prefix* instead of ``settings.COMPRESS_URL``.
    """

    run_with_compression_disabled = True

    def post_process_url(self, url):
        """
        Replace ``settings.COMPRESS_URL`` URL prefix with  '../' * (N + 1)
        where N is the *depth* of ``settings.COMPRESS_OUTPUT_DIR`` folder.

        E.g. by default ``settings.COMPRESS_OUTPUT_DIR == 'CACHE'``,
        the depth is 1, and the prefix will be '../../'.

        If ``settings.COMPRESS_OUTPUT_DIR == 'my/compiled/data'``,
        the depth is 3, and the prefix will be '../../../../'.

        Example:

        - original file URL: '/static/my-app/style.css'
        - it has an image link: ``url(images/logo.svg)``
        - compiled file URL: '/static/CACHE/css/output.abcdef123456.css'
        - replaced image link URL: ``url(../../my-app/images/logo.svg)``
        """
        old_prefix = self.url
        if self.has_scheme:
            old_prefix = '{}{}'.format(self.protocol, old_prefix)
        # One level up from 'css' / 'js' folder
        new_prefix = '..'
        # N levels up from ``settings.COMPRESS_OUTPUT_DIR``
        new_prefix += '/..' * len(list(filter(
            None, os.path.normpath(settings.COMPRESS_OUTPUT_DIR).split(os.sep)
        )))
        return re.sub('^{}'.format(old_prefix), new_prefix, url)
