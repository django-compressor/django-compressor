from compressor.tests.base import (CompressorTestCase, CssMediaTestCase,
    VerboseTestCase, CacheBackendTestCase)
from compressor.tests.filters import (CssTidyTestCase, PrecompilerTestCase,
    CssMinTestCase, CssAbsolutizingTestCase, CssAbsolutizingTestCaseWithHash,
    CssDataUriTestCase)
from compressor.tests.jinja2ext import TestJinja2CompressorExtension
from compressor.tests.offline import (
    OfflineGenerationBlockSuperTestCase, OfflineGenerationConditionTestCase,
    OfflineGenerationTemplateTagTestCase, OfflineGenerationTestCaseWithContext,
    OfflineGenerationTestCaseErrors, OfflineGenerationTestCase)
from compressor.tests.parsers import (LxmlParserTests, Html5LibParserTests,
    BeautifulSoupParserTests, HtmlParserTests)
from compressor.tests.signals import PostCompressSignalTestCase
from compressor.tests.storages import StorageTestCase
from compressor.tests.templatetags import (TemplatetagTestCase,
    PrecompilerTemplatetagTestCase)
