from subprocess import Popen, PIPE

from compressor.conf import settings
from compressor.filters import FilterBase, FilterError
from compressor.utils import cmd_split


class UglifyJSFilter(FilterBase):

    def output(self, **kwargs):
        arguments = settings.COMPRESS_UGLIFY_ARGUMENTS
        command = '%s %s' % (settings.COMPRESS_UGLIFY_BINARY, arguments)

        try:
            p = Popen(cmd_split(command), stdout=PIPE, stdin=PIPE, stderr=PIPE)
            filtered, err = p.communicate(self.content)

        except IOError, e:
            raise FilterError(e)

        if p.wait() != 0:
            if not err:
                err = 'Unable to apply UglifyJS filter'
            raise FilterError(err)

        if self.verbose:
            print err

        return filtered
