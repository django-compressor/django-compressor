from .base import CompressorTestCase, CssMediaTestCase, VerboseTestCase, CacheBackendTestCase
from .filters import CssTidyTestCase, PrecompilerTestCase, CssMinTestCase, CssAbsolutizingTestCase, CssDataUriTestCase
from .offline import OfflineGenerationTestCase
from .parsers import LxmlParserTests, Html5LibParserTests, BeautifulSoupParserTests, HtmlParserTests
from .signals import PostCompressSignalTestCase
from .storages import StorageTestCase
from .templatetags import TemplatetagTestCase
