import os
import warnings
import tempfile

from compressor.conf import settings
from compressor.filters import FilterBase, FilterError

warnings.simplefilter('ignore', RuntimeWarning)

class LessFilter(FilterBase):

    def output(self, **kwargs):
        
        tmp_file = tempfile.NamedTemporaryFile(mode='w+b')
        tmp_file.write(self.content)
        tmp_file.flush()
        
        output_file = tempfile.NamedTemporaryFile(mode='w+b')
        
        command = '%s %s %s' % (settings.LESSC_BINARY, tmp_file.name, output_file.name)

        command_output = os.popen(command).read()
        
        filtered_css = output_file.read()
        output_file.close()
        tmp_file.close()
        
        if self.verbose:
            print command_output
        
        return filtered_css
