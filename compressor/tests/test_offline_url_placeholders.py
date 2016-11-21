from django.test.utils import override_settings

import compressor.tests.test_offline


module_dict = globals()


for key in dir(compressor.tests.test_offline):
    if key.startswith('OfflineCompress') and key.endswith('TestCase'):
        base_class = getattr(compressor.tests.test_offline, key)
        new_class_name = key[:15] + 'WithUrlPlaceholders' + key[15:]
        new_class = type(new_class_name, (base_class,), {})
        module_dict[key] = override_settings(COMPRESS_OFFLINE_URL_PLACEHOLDERS=True)(new_class)
