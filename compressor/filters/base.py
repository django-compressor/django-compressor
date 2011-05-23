import logging
import subprocess
import tempfile

from compressor.conf import settings
from compressor.exceptions import FilterError
from compressor.utils import cmd_split, stringformat

logger = logging.getLogger("compressor.filters")


class FilterBase(object):

    def __init__(self, content, filter_type=None, verbose=0):
        self.type = filter_type
        self.content = content
        self.verbose = verbose or settings.COMPRESS_VERBOSE
        self.logger = logger

    def input(self, **kwargs):
        raise NotImplementedError

    def output(self, **kwargs):
        raise NotImplementedError


class CompilerFilter(FilterBase):
    """
    A filter subclass that is able to filter content via
    external commands.
    """
    command = None
    filename = None
    options = {}

    def __init__(self, content, command=None, filename=None, *args, **kwargs):
        super(CompilerFilter, self).__init__(content, *args, **kwargs)
        if command:
            self.command = command
        if self.command is None:
            raise FilterError("Required attribute 'command' not given")
        self.filename = filename
        self.stdout = subprocess.PIPE
        self.stdin = subprocess.PIPE
        self.stderr = subprocess.PIPE

    def output(self, **kwargs):
        infile = None
        outfile = None
        try:
            if "{infile}" in self.command:
                infile = tempfile.NamedTemporaryFile(mode='w')
                infile.write(self.content)
                infile.flush()
                self.options["infile"] = self.filename or infile.name
            if "{outfile}" in self.command:
                ext = ".%s" % self.type and self.type or ""
                outfile = tempfile.NamedTemporaryFile(mode='rw', suffix=ext)
                self.options["outfile"] = outfile.name
            command = stringformat.FormattableString(self.command)
            proc = subprocess.Popen(cmd_split(command.format(**self.options)),
                stdout=self.stdout, stdin=self.stdin, stderr=self.stderr)
            if infile is not None:
                filtered, err = proc.communicate()
            else:
                filtered, err = proc.communicate(self.content)
        except (IOError, OSError), e:
            raise FilterError('Unable to apply %s (%r): %s' %
                              (self.__class__.__name__, self.command, e))
        else:
            if proc.wait() != 0:
                if not err:
                    err = ('Unable to apply %s (%s)' %
                           (self.__class__.__name__, self.command))
                raise FilterError(err)
            if self.verbose:
                self.logger.debug(err)
            if outfile is not None:
                filtered = outfile.read()
        finally:
            if infile is not None:
                infile.close()
            if outfile is not None:
                outfile.close()
        return filtered
