from django.test import TestCase

from compressor.finders import CompressorFinder
from compressor.storage import CompressorFileStorage


class FinderTestCase(TestCase):
    def test_has_correct_storage(self):
        finder = CompressorFinder()
        self.assertTrue(type(finder.storage) is CompressorFileStorage)

    def test_list_returns_empty_list(self):
        finder = CompressorFinder()
        self.assertEqual(finder.list([]), [])
