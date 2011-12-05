from .base import (CompressorTestCase, CssMediaTestCase, VerboseTestCase,
    CacheBackendTestCase)
from .filters import (CssTidyTestCase, PrecompilerTestCase, CssMinTestCase,
    CssAbsolutizingTestCase, CssAbsolutizingTestCaseWithHash,
    CssDataUriTestCase)
from .jinja2ext import TestJinja2CompressorExtension
from .offline import (
    OfflineGenerationBlockSuperTestCase,
    OfflineGenerationConditionTestCase, 
    OfflineGenerationTemplateTagTestCase,
    OfflineGenerationTestCaseWithContext,
    OfflineGenerationTestCaseErrors,
    OfflineGenerationTestCase)
from .parsers import (LxmlParserTests, Html5LibParserTests,
    BeautifulSoupParserTests, HtmlParserTests)
from .signals import PostCompressSignalTestCase
from .storages import StorageTestCase
from .templatetags import TemplatetagTestCase, PrecompilerTemplatetagTestCase
