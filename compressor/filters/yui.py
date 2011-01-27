from subprocess import Popen, PIPE

from compressor.conf import settings
from compressor.filters import FilterBase, FilterError
from compressor.utils import cmd_split


class YUICompressorFilter(FilterBase):

    def output(self, **kwargs):
        arguments = ''
        if self.type == 'js':
            arguments = settings.YUI_JS_ARGUMENTS
        if self.type == 'css':
            arguments = settings.YUI_CSS_ARGUMENTS

        command = '%s --type=%s %s' % (settings.YUI_BINARY, self.type, arguments)

        if self.verbose:
            command += ' --verbose'

        try:
            p = Popen(cmd_split(command), stdin=PIPE, stdout=PIPE, stderr=PIPE)
            filtered, err = p.communicate(self.content)
        except IOError, e:
            raise FilterError(e)

        if p.wait() != 0:
            if not err:
                err = 'Unable to apply YUI Compressor filter'
            raise FilterError(err)

        if self.verbose:
            print err

        return filtered


class YUICSSFilter(YUICompressorFilter):
    def __init__(self, *args, **kwargs):
        super(YUICSSFilter, self).__init__(*args, **kwargs)
        self.type = 'css'


class YUIJSFilter(YUICompressorFilter):
    def __init__(self, *args, **kwargs):
        super(YUIJSFilter, self).__init__(*args, **kwargs)
        self.type = 'js'
