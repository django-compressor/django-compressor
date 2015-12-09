from __future__ import absolute_import, unicode_literals
import io
import logging
import subprocess

from importlib import import_module
from platform import system

if system() != "Windows":
    try:
        from shlex import quote as shell_quote  # Python 3
    except ImportError:
        from pipes import quote as shell_quote  # Python 2
else:
    from subprocess import list2cmdline
    def shell_quote(s):
        # shlex.quote/pipes.quote is not compatible with Windows
        return list2cmdline([s])

from django.core.exceptions import ImproperlyConfigured
from django.core.files.temp import NamedTemporaryFile

from django.utils.encoding import smart_text
from django.utils import six

from compressor.cache import cache, get_precompiler_cachekey

from compressor.conf import settings
from compressor.exceptions import FilterError
from compressor.utils import get_mod_func


logger = logging.getLogger("compressor.filters")


class FilterBase(object):
    """
    A base class for filters that does nothing.

    Subclasses should implement `input` and/or `output` methods which must
    return a string (unicode under python 2) or raise a NotImplementedError.
    """
    def __init__(self, content, attrs=None, filter_type=None, filename=None,
                 verbose=0, charset=None, **kwargs):
        self.type = filter_type or getattr(self, 'type', None)
        self.content = content
        self.verbose = verbose or settings.COMPRESS_VERBOSE
        self.logger = logger
        self.filename = filename
        self.charset = charset

    def input(self, **kwargs):
        raise NotImplementedError

    def output(self, **kwargs):
        raise NotImplementedError


class CallbackOutputFilter(FilterBase):
    """
    A filter which takes function path in `callback` attribute, imports it
    and uses that function to filter output string::

        class MyFilter(CallbackOutputFilter):
            callback = 'path.to.my.callback'

    Callback should be a function which takes a string as first argument and
    returns a string (unicode under python 2).
    """
    callback = None
    args = []
    kwargs = {}
    dependencies = []

    def __init__(self, *args, **kwargs):
        super(CallbackOutputFilter, self).__init__(*args, **kwargs)
        if self.callback is None:
            raise ImproperlyConfigured(
                "The callback filter %s must define a 'callback' attribute." %
                self.__class__.__name__)
        try:
            mod_name, func_name = get_mod_func(self.callback)
            func = getattr(import_module(mod_name), func_name)
        except (ImportError, TypeError):
            if self.dependencies:
                if len(self.dependencies) == 1:
                    warning = "dependency (%s) is" % self.dependencies[0]
                else:
                    warning = ("dependencies (%s) are" %
                               ", ".join([dep for dep in self.dependencies]))
            else:
                warning = ""
            raise ImproperlyConfigured(
                "The callback %s couldn't be imported. Make sure the %s "
                "correctly installed." % (self.callback, warning))
        except AttributeError as e:
            raise ImproperlyConfigured("An error occurred while importing the "
                                       "callback filter %s: %s" % (self, e))
        else:
            self._callback_func = func

    def output(self, **kwargs):
        ret = self._callback_func(self.content, *self.args, **self.kwargs)
        assert isinstance(ret, six.text_type)
        return ret


class CompilerFilter(FilterBase):
    """
    A filter subclass that is able to filter content via
    external commands.
    """
    command = None
    options = ()
    default_encoding = settings.FILE_CHARSET

    def __init__(self, content, command=None, **kwargs):
        super(CompilerFilter, self).__init__(content, **kwargs)
        self.cwd = None

        if command:
            self.command = command
        if self.command is None:
            raise FilterError("Required attribute 'command' not given")

        if isinstance(self.options, dict):
            # turn dict into a tuple
            new_options = ()
            for item in kwargs.items():
                new_options += (item,)
            self.options = new_options

        # append kwargs to self.options
        for item in kwargs.items():
            self.options += (item,)

        self.stdout = self.stdin = self.stderr = subprocess.PIPE
        self.infile = self.outfile = None

    def input(self, **kwargs):

        encoding = self.default_encoding
        options = dict(self.options)

        if self.infile is None and "{infile}" in self.command:
            # create temporary input file if needed
            if self.filename is None:
                self.infile = NamedTemporaryFile(mode='wb')
                self.infile.write(self.content.encode(encoding))
                self.infile.flush()
                options["infile"] = self.infile.name
            else:
                # we use source file directly, which may be encoded using
                # something different than utf8. If that's the case file will
                # be included with charset="something" html attribute and
                # charset will be available as filter's charset attribute
                encoding = self.charset  # or self.default_encoding
                self.infile = open(self.filename)
                options["infile"] = self.filename

        if "{outfile}" in self.command and "outfile" not in options:
            # create temporary output file if needed
            ext = self.type and ".%s" % self.type or ""
            self.outfile = NamedTemporaryFile(mode='r+', suffix=ext)
            options["outfile"] = self.outfile.name

        # Quote infile and outfile for spaces etc.
        if "infile" in options:
            options["infile"] = shell_quote(options["infile"])
        if "outfile" in options:
            options["outfile"] = shell_quote(options["outfile"])

        try:
            command = self.command.format(**options)
            proc = subprocess.Popen(
                command, shell=True, cwd=self.cwd, stdout=self.stdout,
                stdin=self.stdin, stderr=self.stderr)
            if self.infile is None:
                # if infile is None then send content to process' stdin
                filtered, err = proc.communicate(
                    self.content.encode(encoding))
            else:
                filtered, err = proc.communicate()
            filtered, err = filtered.decode(encoding), err.decode(encoding)
        except (IOError, OSError) as e:
            raise FilterError('Unable to apply %s (%r): %s' %
                              (self.__class__.__name__, self.command, e))
        else:
            if proc.wait() != 0:
                # command failed, raise FilterError exception
                if not err:
                    err = ('Unable to apply %s (%s)' %
                           (self.__class__.__name__, self.command))
                    if filtered:
                        err += '\n%s' % filtered
                raise FilterError(err)

            if self.verbose:
                self.logger.debug(err)

            outfile_path = options.get('outfile')
            if outfile_path:
                with io.open(outfile_path, 'r', encoding=encoding) as file:
                    filtered = file.read()
        finally:
            if self.infile is not None:
                self.infile.close()
            if self.outfile is not None:
                self.outfile.close()
        return smart_text(filtered)


class CachedCompilerFilter(CompilerFilter):

    def __init__(self, mimetype, *args, **kwargs):
        self.mimetype = mimetype
        super(CachedCompilerFilter, self).__init__(*args, **kwargs)

    def input(self, **kwargs):
        if self.mimetype in settings.COMPRESS_CACHEABLE_PRECOMPILERS:
            key = self.get_cache_key()
            data = cache.get(key)
            if data is not None:
                return data
            filtered = super(CachedCompilerFilter, self).input(**kwargs)
            cache.set(key, filtered, settings.COMPRESS_REBUILD_TIMEOUT)
            return filtered
        else:
            return super(CachedCompilerFilter, self).input(**kwargs)

    def get_cache_key(self):
        return get_precompiler_cachekey(self.command, self.content)
