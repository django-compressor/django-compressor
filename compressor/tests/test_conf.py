from django.test import SimpleTestCase
from django.test.utils import override_settings
from compressor.conf import settings
from compressor.conf import CompressorConf


default_css_filters = [
    "compressor.filters.css_default.CssAbsoluteFilter",
    "compressor.filters.cssmin.rCSSMinFilter",
]
default_js_filters = ["compressor.filters.jsmin.rJSMinFilter"]


def create_conf(**attrs):
    # Creating a new appconf.AppConf subclass will cause
    # its configuration to be resolved.
    # We use this to force the CompressorConf to be re-resolved,
    # when we've changed the settings.
    attrs["__module__"] = None
    return type("TestCompressorConf", (CompressorConf,), attrs)


class ConfTestCase(SimpleTestCase):
    def test_filter_defaults(self):
        # This used the settings from compressor/test_settings.py
        # which contains no values for filers and therefore uses the defaults.
        self.assertEqual(settings.COMPRESS_FILTERS["css"], default_css_filters)
        self.assertEqual(settings.COMPRESS_FILTERS["js"], default_js_filters)

    @override_settings(COMPRESS_FILTERS=dict(css=["ham"], js=["spam"]))
    def test_filters_by_main_setting(self):
        conf = create_conf()
        self.assertEqual(conf.FILTERS["css"], ["ham"])
        self.assertEqual(conf.FILTERS["js"], ["spam"])

    def test_sri_hashes_defaults(self):
        conf = create_conf()
        self.assertEqual(conf.SRI_HASHES, ())

    @override_settings(COMPRESS_SRI_HASHES=("sha256", "SHA384"))
    def test_sri_hashes_normalized(self):
        conf = create_conf()
        self.assertEqual(conf.SRI_HASHES, ("sha256", "sha384"))

    @override_settings(COMPRESS_SRI_HASHES="sha512")
    def test_sri_hashes_string(self):
        conf = create_conf()
        self.assertEqual(conf.SRI_HASHES, ("sha512",))

    @override_settings(COMPRESS_SRI_HASHES=("md5",))
    def test_sri_hashes_invalid(self):
        with self.assertRaisesMessage(
            Exception, "COMPRESS_SRI_HASHES setting only supports"
        ):
            create_conf()

    @override_settings(COMPRESS_SRI_CROSSORIGIN="anonymous")
    def test_sri_crossorigin(self):
        conf = create_conf()
        self.assertEqual(conf.SRI_CROSSORIGIN, "anonymous")
