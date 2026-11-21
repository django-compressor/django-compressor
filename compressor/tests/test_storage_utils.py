from django.core.files.base import ContentFile
from django.test import TestCase
from io import BytesIO


class StorageUtilsTestCase(TestCase):
    """
    Test utility functions for storage handling
    """

    def setUp(self):
        self.test_string = b"test content"
        self.test_file = ContentFile(self.test_string)

    def test_content_seek_operations(self):
        """Test seek operations on different content types"""
        # ContentFile should support seek operations
        content = ContentFile(b"test data")
        content.seek(0)  # Seek to beginning
        self.assertEqual(content.tell(), 0)
        content.seek(4)  # Seek to position 4
        self.assertEqual(content.tell(), 4)
        self.assertEqual(content.read(), b" data")

        # BytesIO should support seek operations
        bytesio = BytesIO(b"test data")
        bytesio.seek(0)
        self.assertEqual(bytesio.tell(), 0)
        bytesio.seek(5)
        self.assertEqual(bytesio.tell(), 5)
        self.assertEqual(bytesio.read(), b"data")

    def test_file_copying(self):
        """Test making copies of file objects"""
        # Make a copy of ContentFile
        content = ContentFile(b"test data")
        content.seek(2)  # Move position

        # Create a new BytesIO with the content
        from django.core.files import File
        content.seek(0)  # Reset position
        content_copy = File(BytesIO(content.read()))

        # Original file's position should not be affected
        self.assertEqual(content.tell(), 9)  # After reading all content

        # Copy should have its own position
        self.assertEqual(content_copy.tell(), 0)  # New file starts at beginning
        self.assertEqual(content_copy.read(), b"test data")

        # Reset both files
        content.seek(0)
        content_copy.seek(0)

        # Both should read the same content
        self.assertEqual(content.read(), b"test data")
        self.assertEqual(content_copy.read(), b"test data")