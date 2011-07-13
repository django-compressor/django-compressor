import os
from compressor.conf import settings as compressor_settings
from django.conf import settings as global_settings
from django.core.exceptions import ImproperlyConfigured

from compressor.utils.settings import AppSettings

class CompassSettings(AppSettings):

    ENABLED = global_settings.DEBUG
    CONFIG = 'config.rb'
    WHERE = ''
    BINARY = 'compass'

    def configure_config(self, value):
        config_path = os.path.join(compressor_settings.COMPRESS_ROOT, value)
        if not os.path.isfile(config_path):
            raise ImproperlyConfigured("COMPASS_CONFIG setting is not a config \
                file to compass: %s" % config_path)
        return os.path.abspath(config_path)

    def configure_where(self, value):
        if not value:
            value = os.path.abspath(os.path.dirname(self.COMPASS_CONFIG))
        else:
            if not os.path.isdir(value):
                raise ImproperlyConfigured("COMPASS_WHERE setting is not set to \
                    a valid directory to generate compass files: %s" % value)
        return value

settings = CompassSettings(prefix='COMPASS')
