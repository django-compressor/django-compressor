from subprocess import Popen, PIPE
import tempfile
import warnings

from django.conf import settings

from compressor.filters import FilterBase

BINARY = getattr(settings, 'CSSTIDY_BINARY', 'csstidy')
ARGUMENTS = getattr(settings, 'CSSTIDY_ARGUMENTS', '--template=highest')

warnings.simplefilter('ignore', RuntimeWarning)

class CSSTidyFilter(FilterBase):
    def output(self, **kwargs):
        tmp_file = tempfile.NamedTemporaryFile(mode='w+b')
        tmp_file.write(self.content)
        tmp_file.flush()

        output_file = tempfile.NamedTemporaryFile(mode='w+b')

        command = '%s %s %s %s' % (BINARY, tmp_file.name, ARGUMENTS, output_file.name)

        command_output = Popen(command, shell=True,
            stdout=PIPE, stdin=PIPE, stderr=PIPE).communicate()

        filtered_css = output_file.read()
        output_file.close()
        tmp_file.close()

        if self.verbose:
            print command_output

        return filtered_css
