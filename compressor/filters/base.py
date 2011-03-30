import os
import logging
import subprocess
import tempfile

from compressor.conf import settings
from compressor.exceptions import FilterError
from compressor.utils import cmd_split

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
    def __init__(self, content, filter_type=None, verbose=0, command=None):
        super(CompilerFilter, self).__init__(content, filter_type, verbose)
        if command:
            self.command = command
        if not self.command:
            raise FilterError("Required command attribute not set")
        self.options = {}
        self.stdout = subprocess.PIPE
        self.stdin = subprocess.PIPE
        self.stderr = subprocess.PIPE

    def output(self, **kwargs):
        infile = outfile = ""
        try:
            if "%(infile)s" in self.command:
                infile = tempfile.NamedTemporaryFile(mode='w')
                infile.write(self.content)
                infile.flush()
                self.options["infile"] = infile.name
            if "%(outfile)s" in self.command:
                ext = ".%s" % self.type and self.type or ""
                outfile = tempfile.NamedTemporaryFile(mode='w', suffix=ext)
                self.options["outfile"] = outfile.name
            proc = subprocess.Popen(cmd_split(self.command % self.options),
                stdout=self.stdout, stdin=self.stdin, stderr=self.stderr)
            if infile:
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
        if outfile:
            try:
                outfile_obj = open(outfile.name)
                filtered = outfile_obj.read()
            finally:
                outfile_obj.close()
        return filtered
