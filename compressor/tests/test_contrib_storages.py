import os
import unittest
from unittest import mock

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings


class ContribStoragesTestCase(TestCase):
    """
    Test cases for the contrib storage backends
    """
    def setUp(self):
        self.test_string = b"test content"
        self.test_file = ContentFile(self.test_string)


# Only run S3 tests if boto3 is installed
try:
    import boto3
    from compressor.contrib.storages.s3 import CachedS3BotoStorage, CachedS3BotoStaticStorage
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


@unittest.skipIf(not HAS_BOTO3, "boto3 not installed")
class S3StorageTestCase(ContribStoragesTestCase):

    @mock.patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_cached_s3_storage_save_local(self, mock_s3_save):
        """Test that the cached S3 storage saves locally"""
        # Mock the S3 save to return the filename
        mock_s3_save.return_value = 'test.txt'

        # Create a storage instance with mocked local storage
        storage = CachedS3BotoStorage()
        storage.local_storage = mock.MagicMock()

        # Save a file
        storage.save('test.txt', self.test_file)

        # Verify local save was called
        storage.local_storage._save.assert_called_once()
        self.assertEqual(storage.local_storage._save.call_args[0][0], 'test.txt')


# Only run GCS tests if google-cloud-storage is installed
try:
    import google.cloud.storage
    from compressor.contrib.storages.gcloud import CachedGoogleCloudStorage
    HAS_GCS = True
except ImportError:
    HAS_GCS = False


@unittest.skipIf(not HAS_GCS, "google-cloud-storage not installed")
class GCSStorageTestCase(ContribStoragesTestCase):

    @mock.patch('storages.backends.gcloud.GoogleCloudStorage.save')
    def test_cached_gcs_storage_save_local(self, mock_gcs_save):
        """Test that the cached GCS storage saves locally"""
        # Mock the GCS save to return the filename
        mock_gcs_save.return_value = 'test.txt'

        # Create a storage instance with mocked local storage
        storage = CachedGoogleCloudStorage()
        storage.local_storage = mock.MagicMock()

        # Save a file
        storage.save('test.txt', self.test_file)

        # Verify local save was called
        storage.local_storage._save.assert_called_once()
        self.assertEqual(storage.local_storage._save.call_args[0][0], 'test.txt')


# Only run Azure tests if azure-storage-blob is installed
try:
    import azure.storage.blob
    from compressor.contrib.storages.azure import CachedAzureStorage
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False


@unittest.skipIf(not HAS_AZURE, "azure-storage-blob not installed")
class AzureStorageTestCase(ContribStoragesTestCase):

    @mock.patch('storages.backends.azure_storage.AzureStorage.save')
    def test_cached_azure_storage_save_local(self, mock_azure_save):
        """Test that the cached Azure storage saves locally"""
        # Mock the Azure save to return the filename
        mock_azure_save.return_value = 'test.txt'

        # Create a storage instance with mocked local storage
        storage = CachedAzureStorage()
        storage.local_storage = mock.MagicMock()

        # Save a file
        storage.save('test.txt', self.test_file)

        # Verify local save was called
        storage.local_storage._save.assert_called_once()
        self.assertEqual(storage.local_storage._save.call_args[0][0], 'test.txt')
