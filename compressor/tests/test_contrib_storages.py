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

    def test_content_handling_utils(self):
        """Test utility function for content handling"""
        # Test creating a copy of a file-like object
        from io import BytesIO
        from django.core.files import File

        # Regular content file
        content = ContentFile(b"test data")
        self.assertEqual(content.read(), b"test data")
        content.seek(0)  # Reset for next read

        # File wrapper around BytesIO
        file_obj = BytesIO(b"test data")
        file_wrapper = File(file_obj)
        self.assertEqual(file_wrapper.read(), b"test data")
        file_wrapper.seek(0)  # Reset position


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

    @mock.patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_cached_s3_storage_with_seekable_content(self, mock_s3_save):
        """Test that the cached S3 storage handles seekable content correctly"""
        mock_s3_save.return_value = 'test.txt'

        # Create a BytesIO object to simulate a file with seek capabilities
        from io import BytesIO
        seekable_content = ContentFile(BytesIO(self.test_string).read())

        storage = CachedS3BotoStorage()
        storage.local_storage = mock.MagicMock()

        storage.save('test.txt', seekable_content)

        # Verify content position was reset after S3 save
        mock_s3_save.assert_called_once()
        storage.local_storage._save.assert_called_once()

    @mock.patch('storages.backends.s3boto3.S3Boto3Storage.__init__')
    @mock.patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_cached_s3_static_storage_init_parameters(self, mock_s3_save, mock_s3_init):
        """Test that CachedS3BotoStaticStorage passes correct parameters to parent class"""
        mock_s3_init.return_value = None
        mock_s3_save.return_value = 'test.txt'

        with override_settings(
            AWS_STATIC_BUCKET_NAME='static-bucket',
            AWS_STATIC_LOCATION='static',
            AWS_STATIC_QUERYSTRING_AUTH=False,
            AWS_STATIC_CUSTOM_DOMAIN='static.example.com',
            AWS_STATIC_FILE_OVERWRITE=True,
            AWS_STATIC_OBJECT_PARAMETERS={'CacheControl': 'max-age=86400'}
        ):
            storage = CachedS3BotoStaticStorage()
            storage.local_storage = mock.MagicMock()
            storage.save('test.txt', self.test_file)

            # Verify S3Boto3Storage was initialized with the correct parameters
            call_kwargs = mock_s3_init.call_args[1]
            self.assertEqual(call_kwargs.get('bucket_name'), 'static-bucket')
            self.assertEqual(call_kwargs.get('location'), 'static')
            self.assertEqual(call_kwargs.get('querystring_auth'), False)
            self.assertEqual(call_kwargs.get('custom_domain'), 'static.example.com')
            self.assertEqual(call_kwargs.get('file_overwrite'), True)
            self.assertEqual(call_kwargs.get('object_parameters'), {'CacheControl': 'max-age=86400'})


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

    @mock.patch('storages.backends.gcloud.GoogleCloudStorage.save')
    def test_cached_gcs_storage_with_non_seekable_content(self, mock_gcs_save):
        """Test that the cached GCS storage handles non-seekable content correctly"""
        mock_gcs_save.return_value = 'test.txt'

        # Create a mock content object without a file attribute
        non_seekable_content = mock.MagicMock(spec=[])

        storage = CachedGoogleCloudStorage()
        storage.local_storage = mock.MagicMock()

        storage.save('test.txt', non_seekable_content)

        # Verify saves still work with non-seekable content
        mock_gcs_save.assert_called_once()
        storage.local_storage._save.assert_called_once()
        self.assertEqual(storage.local_storage._save.call_args[0][0], 'test.txt')
        self.assertEqual(storage.local_storage._save.call_args[0][1], non_seekable_content)

    @mock.patch('storages.backends.gcloud.GoogleCloudStorage.__init__')
    @mock.patch('storages.backends.gcloud.GoogleCloudStorage.save')
    def test_cached_gcs_static_storage_init_parameters(self, mock_gcs_save, mock_gcs_init):
        """Test that CachedGoogleCloudStaticStorage passes correct parameters to parent class"""
        mock_gcs_init.return_value = None
        mock_gcs_save.return_value = 'test.txt'

        with override_settings(
            GS_STATIC_BUCKET_NAME='static-bucket',
            GS_STATIC_LOCATION='static',
            GS_STATIC_CUSTOM_ENDPOINT='https://storage.googleapis.com',
            GS_STATIC_DEFAULT_ACL='publicRead',
            GS_STATIC_FILE_OVERWRITE=True,
            GS_STATIC_CACHE_CONTROL='max-age=86400'
        ):
            from compressor.contrib.storages.gcloud import CachedGoogleCloudStaticStorage
            storage = CachedGoogleCloudStaticStorage()
            storage.local_storage = mock.MagicMock()
            storage.save('test.txt', self.test_file)

            # Verify GoogleCloudStorage was initialized with the correct parameters
            call_kwargs = mock_gcs_init.call_args[1]
            self.assertEqual(call_kwargs.get('bucket_name'), 'static-bucket')
            self.assertEqual(call_kwargs.get('location'), 'static')
            self.assertEqual(call_kwargs.get('custom_endpoint'), 'https://storage.googleapis.com')
            self.assertEqual(call_kwargs.get('default_acl'), 'publicRead')
            self.assertEqual(call_kwargs.get('file_overwrite'), True)
            self.assertEqual(call_kwargs.get('cache_control'), 'max-age=86400')


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

    @mock.patch('storages.backends.azure_storage.AzureStorage.save')
    def test_cached_azure_storage_with_file_content(self, mock_azure_save):
        """Test that the cached Azure storage handles file content correctly"""
        mock_azure_save.return_value = 'test.txt'

        # Create a file-like object with seek method
        from io import BytesIO
        file_content = ContentFile(BytesIO(self.test_string).read())

        storage = CachedAzureStorage()
        storage.local_storage = mock.MagicMock()

        storage.save('test.txt', file_content)

        # Verify file content was properly handled
        mock_azure_save.assert_called_once()
        storage.local_storage._save.assert_called_once()

    @mock.patch('storages.backends.azure_storage.AzureStorage.__init__')
    @mock.patch('storages.backends.azure_storage.AzureStorage.save')
    def test_cached_azure_static_storage_init_parameters(self, mock_azure_save, mock_azure_init):
        """Test that CachedAzureStaticStorage passes correct parameters to parent class"""
        mock_azure_init.return_value = None
        mock_azure_save.return_value = 'test.txt'

        with override_settings(
            AZURE_STATIC_CONTAINER='static-container',
            AZURE_STATIC_EXPIRATION_TIMEOUT=3600
        ):
            from compressor.contrib.storages.azure import CachedAzureStaticStorage
            storage = CachedAzureStaticStorage()
            storage.local_storage = mock.MagicMock()
            storage.save('test.txt', self.test_file)

            # Verify AzureStorage was initialized with the correct parameters
            call_kwargs = mock_azure_init.call_args[1]
            self.assertEqual(call_kwargs.get('azure_container'), 'static-container')
            self.assertEqual(call_kwargs.get('expiration_secs'), 3600)
