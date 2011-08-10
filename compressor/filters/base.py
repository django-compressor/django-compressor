import os
import logging
import subprocess
import tempfile

from compressor.conf import settings
from compressor.exceptions import FilterError
from compressor.utils.stringformat import FormattableString as fstr

logger = logging.getLogger("compressor.filters")


class FilterBase(object):

    def __init__(self, content, filter_type=None, filename=None, verbose=0):
        self.type = filter_type
        self.content = content
        self.verbose = verbose or settings.COMPRESS_VERBOSE
        self.logger = logger
        self.filename = filename

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
    options = ()

    def __init__(self, content, command=None, *args, **kwargs):
        super(CompilerFilter, self).__init__(content, *args, **kwargs)
        self.cwd = None
        if command:
            self.command = command
        if self.command is None:
            raise FilterError("Required attribute 'command' not given")
        if isinstance(self.options, dict):
            new_options = ()
            for item in kwargs.iteritems():
                new_options += (item,)
            self.options = new_options
        for item in kwargs.iteritems():
            self.options += (item,)
        self.stdout = subprocess.PIPE
        self.stdin = subprocess.PIPE
        self.stderr = subprocess.PIPE
        self.infile, self.outfile = None, None

    def input(self, **kwargs):
        options = dict(self.options)
        delete_temp_in, delete_temp_out = False, False
        if self.infile is None:
            if "{infile}" in self.command:
                if self.filename is None:
                    delete_temp_in = True
                    self.infile, options["infile"] = tempfile.mkstemp()
                    self.infile = os.fdopen(self.infile, "wb")
                    self.infile.write(self.content)
                    self.infile.flush()
                    os.fsync(self.infile)
                else:
                    delete_temp_out = True
                    self.infile = open(self.filename)
                    options["infile"] = self.filename

        if "{outfile}" in self.command and not "outfile" in options:
            self.outfile, options["outfile"] = tempfile.mkstemp()
            self.outfile = os.fdopen(self.outfile, "r+b")
        try:
            command = fstr(self.command).format(**options)
            proc = subprocess.Popen(command, shell=True, cwd=self.cwd,
                stdout=self.stdout, stdin=self.stdin, stderr=self.stderr)
            if self.infile is None:
                filtered, err = proc.communicate(self.content)
            else:
                filtered, err = proc.communicate()
        except (IOError, OSError), e:
            raise FilterError('Unable to apply %s (%r): %s' %
                              (self.__class__.__name__, self.command, e))
        else:
            if proc.wait() != 0:
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
                self.outfile = open(outfile_path, 'r')
        finally:
            if self.infile is not None:
                self.infile.close()
                if delete_temp_in:
                    os.remove(options["infile"])
            if self.outfile is not None:
                filtered = self.outfile.read()
                self.outfile.close()
                if delete_temp_out:
                    os.remove(options["outfile"])
        return filtered
