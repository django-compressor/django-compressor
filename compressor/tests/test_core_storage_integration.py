import os
import unittest
from unittest import mock

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from compressor.storage import CompressorFileStorage


class CompressorStorageIntegrationTestCase(TestCase):
    """Tests integration between core CompressorFileStorage and contrib storage backends"""

    def setUp(self):
        self.test_content = b"test compressed content"
        self.test_file = ContentFile(self.test_content)
        self.local_storage = CompressorFileStorage()

    def test_compressor_file_storage_compatibility(self):
        """Test that CompressorFileStorage works as expected for the local_storage in cached backends"""
        # Create a temp file using the storage
        filename = 'test_compressed.css'
        saved_name = self.local_storage.save(filename, self.test_file)

        # Verify the file exists and has correct content
        self.assertTrue(self.local_storage.exists(saved_name))
        with self.local_storage.open(saved_name) as f:
            self.assertEqual(f.read(), self.test_content)

        # Clean up
        self.local_storage.delete(saved_name)


# Only run S3 integration tests if boto3 is installed
try:
    import boto3
    from compressor.contrib.storages.s3 import CachedS3BotoStorage
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


@unittest.skipIf(not HAS_BOTO3, "boto3 not installed")
class S3StorageIntegrationTestCase(CompressorStorageIntegrationTestCase):

    @mock.patch('storages.backends.s3boto3.S3Boto3Storage.save')
    @mock.patch('storages.backends.s3boto3.S3Boto3Storage._normalize_name')
    def test_s3_cached_storage_integration(self, mock_normalize, mock_s3_save):
        """Test integration between S3 cached storage and CompressorFileStorage"""
        mock_normalize.return_value = 'test_compressed.css'
        mock_s3_save.return_value = 'test_compressed.css'

        # Create storage and monkey patch to use our test local storage
        storage = CachedS3BotoStorage()
        storage.local_storage = self.local_storage

        # Save a file
        saved_name = storage.save('test_compressed.css', self.test_file)

        # Verify file was saved locally
        self.assertTrue(self.local_storage.exists(saved_name))
        with self.local_storage.open(saved_name) as f:
            self.assertEqual(f.read(), self.test_content)

        # Clean up
        self.local_storage.delete(saved_name)
