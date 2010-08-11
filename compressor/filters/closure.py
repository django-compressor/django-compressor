import subprocess

from compressor.conf import settings
from compressor.filters import FilterBase, FilterError


class ClosureCompilerFilter(FilterBase):

    def output(self, **kwargs):
        arguments = settings.CLOSURE_COMPILER_ARGUMENTS

        command = '%s %s' % (settings.CLOSURE_COMPILER_BINARY, arguments)

        try:
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            p.stdin.write(self.content)
            p.stdin.close()

            filtered = p.stdout.read()
            p.stdout.close()

            err = p.stderr.read()
            p.stderr.close()
        except IOError, e:
            raise FilterError(e)

        if p.wait() != 0:
            if not err:
                err = 'Unable to apply Closure Compiler filter'
            raise FilterError(err)

        if self.verbose:
            print err

        return filtered

