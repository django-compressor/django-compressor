import pytest
from django.test import TestCase
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from unittest.mock import patch, MagicMock
from django_compressor.contrib.storages import CachedS3Boto3Storage

class TestCachedS3Boto3Storage(TestCase):
    @pytest.fixture(autouse=True)
    def setup_storage(self, tmpdir):
        self.local_storage = FileSystemStorage(location=str(tmpdir))
        self.storage = CachedS3Boto3Storage()
        self.storage.local_storage = self.local_storage

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_save_to_s3_and_local(self, mock_s3_save):
        mock_s3_save.return_value = "test.css"
        content = ContentFile(b"body { color: red; }")
        name = self.storage.save("test.css", content)
        assert mock_s3_save.called
        assert name == "test.css"
        assert self.local_storage.exists("test.css")
        with self.local_storage.open("test.css") as f:
            assert f.read() == b"body { color: red; }"

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_save_with_gzip(self, mock_s3_save):
        mock_s3_save.side_effect = lambda name, content: name
        content = ContentFile(b"body { color: blue; }")
        self.storage.gzip = True
        name = self.storage.save("test.css", content)
        assert self.local_storage.exists("test.css")
        with self.local_storage.open("test.css") as f:
            assert f.read() == b"body { color: blue; }"

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    @patch('django_compressor.contrib.storages.DJANGO_VERSION', (1, 4, 0))
    def test_save_django_1_4(self, mock_s3_save):
        mock_s3_save.return_value = "test.css"
        content = ContentFile(b"body { color: green; }")
        name = self.storage.save("test.css", content)
        assert name == "test.css"
        assert self.local_storage.exists("test.css")
        with self.local_storage.open("test.css") as f:
            assert f.read() == b"body { color: green; }"

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_save_pointer_restored(self, mock_s3_save):
        mock_s3_save.return_value = "test.css"
        content = ContentFile(b"0123456789")
        content.seek(5)
        self.storage.save("test.css", content)
        # After save, pointer should be restored to 5
        assert content.tell() == 5

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_save_binary_file(self, mock_s3_save):
        mock_s3_save.return_value = "test.bin"
        content = ContentFile(b"\x00\x01\x02\x03\x04")
        name = self.storage.save("test.bin", content)
        assert self.local_storage.exists("test.bin")
        with self.local_storage.open("test.bin", "rb") as f:
            assert f.read() == b"\x00\x01\x02\x03\x04"

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_save_text_file(self, mock_s3_save):
        mock_s3_save.return_value = "test.txt"
        content = ContentFile("hello world".encode("utf-8"))
        name = self.storage.save("test.txt", content)
        assert self.local_storage.exists("test.txt")
        with self.local_storage.open("test.txt", "rb") as f:
            assert f.read() == b"hello world"

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_headers_and_settings(self, mock_s3_save):
        mock_s3_save.return_value = "test.css"
        self.storage.headers = {"Cache-Control": "max-age=123"}
        self.storage.gzip = False
        content = ContentFile(b"body { color: purple; }")
        name = self.storage.save("test.css", content)
        assert self.storage.headers["Cache-Control"] == "max-age=123"
        assert self.storage.gzip is False

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_local_storage_not_called_on_s3_failure(self, mock_s3_save):
        mock_s3_save.side_effect = Exception("S3 error")
        content = ContentFile(b"fail")
        # Patch local_storage._save to ensure it's not called
        self.storage.local_storage._save = MagicMock()
        with pytest.raises(Exception):
            self.storage.save("fail.css", content)
        assert not self.storage.local_storage._save.called

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_save_when_file_already_exists(self, mock_s3_save):
        mock_s3_save.return_value = "exists.css"
        content = ContentFile(b"body { color: orange; }")
        # Save once
        self.storage.save("exists.css", content)
        # Save again with different content
        content2 = ContentFile(b"body { color: yellow; }")
        self.storage.save("exists.css", content2)
        # Should overwrite local file
        with self.local_storage.open("exists.css") as f:
            assert f.read() == b"body { color: yellow; }"

    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_local_file_not_gzipped(self, mock_s3_save):
        # Simulate S3 gzipping by changing content before local save
        def s3_save(name, content):
            content.seek(0)
            content._was_gzipped = True
            return name
        mock_s3_save.side_effect = s3_save
        content = ContentFile(b"plain text")
        name = self.storage.save("plain.txt", content)
        assert self.local_storage.exists("plain.txt")
        with self.local_storage.open("plain.txt", "rb") as f:
            assert f.read() == b"plain text"
