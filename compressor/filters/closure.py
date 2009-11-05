import subprocess

from django.conf import settings

from compressor.filters import FilterBase, FilterError

BINARY = getattr(settings, 'COMPRESS_CLOSURE_COMPILER_BINARY', 'java -jar compiler.jar')
ARGUMENTS = getattr(settings, 'COMPRESS_CLOSURE_COMPILER_ARGUMENTS', '')

class ClosureCompilerFilter(FilterBase):

    def output(self, **kwargs):
        arguments = ARGUMENTS

        command = '%s %s' % (BINARY, arguments)

        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        p.stdin.write(self.content)
        p.stdin.close()

        filtered = p.stdout.read()
        p.stdout.close()

        err = p.stderr.read()
        p.stderr.close()

        if p.wait() != 0:
            if not err:
                err = 'Unable to apply Closure Compiler filter'

            raise FilterError(err)

        if self.verbose:
            print err

        return filtered

