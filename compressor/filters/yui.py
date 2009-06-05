import subprocess

from django.conf import settings

from compressor.filters import FilterBase, FilterError

BINARY = getattr(settings, 'COMPRESS_YUI_BINARY', 'java -jar yuicompressor.jar')
CSS_ARGUMENTS = getattr(settings, 'COMPRESS_YUI_CSS_ARGUMENTS', '')
JS_ARGUMENTS = getattr(settings, 'COMPRESS_YUI_JS_ARGUMENTS', '')

class YUICompressorFilter(FilterBase):

    def output(self, **kwargs):
        arguments = ''
        if self.type == 'js':
            arguments = JS_ARGUMENTS
        if self.type == 'css':
            arguments = CSS_ARGUMENTS
            
        command = '%s --type=%s %s' % (BINARY, self.type, arguments)

        if self.verbose:
            command += ' --verbose'

        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        p.stdin.write(self.content)
        p.stdin.close()

        filtered = p.stdout.read()
        p.stdout.close()

        err = p.stderr.read()
        p.stderr.close()

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
