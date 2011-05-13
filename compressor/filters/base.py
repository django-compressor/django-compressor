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

    def __init__(self, content, filter_type=None, verbose=0, command=None, filename=None, **kwargs):
        super(CompilerFilter, self).__init__(content, filter_type, verbose)
        if command:
            self.command = command
        self.options.update(kwargs)
        if self.command is None:
            raise FilterError("Required command attribute not set")
        if filename:
            self.filename = filename
        self.stdout = subprocess.PIPE
        self.stdin = subprocess.PIPE
        self.stderr = subprocess.PIPE

    def output(self, **kwargs):
        infile = None
        outfile = None
        try:
            if "{infile}" in self.command:
                if not self.filename:
                    infile = tempfile.NamedTemporaryFile(mode='w')
                    infile.write(self.content)
                    infile.flush()
                    self.options["infile"] = infile.name
                else:
                    self.options["infile"] = self.filename
            if "{outfile}" in self.command:
                ext = ".%s" % self.type and self.type or ""
                outfile = tempfile.NamedTemporaryFile(mode='w', suffix=ext)
                self.options["outfile"] = outfile.name
            cmd = stringformat.FormattableString(self.command).format(**self.options)
            proc = subprocess.Popen(cmd_split(cmd),
                stdout=self.stdout, stdin=self.stdin, stderr=self.stderr)
            if infile is not None or self.filename is not None:
                filtered, err = proc.communicate()
            else:
                filtered, err = proc.communicate(self.content)
        except (IOError, OSError), e:
            raise FilterError('Unable to apply %s (%r): %s' % (
                self.__class__.__name__, self.command, e))
        finally:
            if infile:
                infile.close()
        if proc.wait() != 0:
            if not err:
                err = 'Unable to apply %s (%s)' % (
                    self.__class__.__name__, self.command)
            raise FilterError(err)
        if self.verbose:
            self.logger.debug(err)
        if outfile is not None:
            try:
                outfile_obj = open(outfile.name)
                filtered = outfile_obj.read()
            finally:
                outfile_obj.close()
        return filtered
