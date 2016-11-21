from django.test import TestCase
from django.test.utils import override_settings

import compressor.tests.test_offline


module_dict = globals()


for key in dir(compressor.tests.test_offline):
    value = getattr(compressor.tests.test_offline, key)
    if isinstance(value, type) and issubclass(value, TestCase):
        new_class = type(key, (value,), {})
        module_dict[key] = override_settings(COMPRESS_OFFLINE_URL_PLACEHOLDERS=True)(new_class)
