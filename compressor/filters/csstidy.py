from subprocess import Popen, PIPE
import tempfile
import warnings

from compressor.conf import settings
from compressor.filters import FilterBase

warnings.simplefilter('ignore', RuntimeWarning)

class CSSTidyFilter(FilterBase):

    def output(self, **kwargs):
        tmp_file = tempfile.NamedTemporaryFile(mode='w+b')
        tmp_file.write(self.content)
        tmp_file.flush()

        output_file = tempfile.NamedTemporaryFile(mode='w+b')

        command = '%s %s %s %s' % (settings.CSSTIDY_BINARY, tmp_file.name, settings.CSSTIDY_ARGUMENTS, output_file.name)

        command_output = Popen(command, shell=True,
            stdout=PIPE, stdin=PIPE, stderr=PIPE).communicate()

        filtered_css = output_file.read()
        output_file.close()
        tmp_file.close()

        if self.verbose:
            print command_output

        return filtered_css
