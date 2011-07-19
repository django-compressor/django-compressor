import re
import subprocess
import logging

from compressor.compass.conf import settings
from compressor.exceptions import FilterError

logger = logging.getLogger("compressor.filters")

class CompassWrapper(object):
    def __init__(self):
        self.stdout = subprocess.PIPE
        self.stderr = subprocess.PIPE
        self.working_dir = settings.COMPASS_WHERE
        self.config = settings.COMPASS_CONFIG
        self.command = [settings.COMPASS_BINARY, 'compile', '--boring']
    
    def compile(self):
        if not settings.COMPASS_ENABLED:
            return False
        
        self.command += ['-c', self.config]
        try:
            command = ' '.join(self.command)
            compiling = subprocess.Popen(command, shell=True, stdout=self.stdout, 
                stderr=self.stderr, cwd=self.working_dir)
            work, err = compiling.communicate()
        except (IOError, OSError), e:
            raise FilterError('Unable to apply %s (%r): %s' %
                              (self.__class__.__name__, command, e))
        else:
            compiling.wait()
            if compiling.returncode != 0:
                # Let compressor or 404 fail if compass isn't installed
                if not re.match('.*%s: not found.*' % settings.COMPASS_BINARY, err):
                    raise FilterError('%s compile fail:\n%s' %
                        (self.__class__.__name__, work))
            logger.debug(work)
            print work
