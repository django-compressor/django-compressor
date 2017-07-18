from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils.six import StringIO


class TestMtimeCacheCommand(TestCase):
    # FIXME: add actual tests, improve the existing ones.

    exclusion_patterns = [
        '*CACHE*', '*custom*', '*066cd253eada.js', '*d728fc7f9301.js', '*74e158ccb432.js', 'test.txt*'
    ]

    def default_ignore(self):
        return ['--ignore=%s' % pattern for pattern in self.exclusion_patterns]

    def test_handle_no_args(self):
        with self.assertRaises(CommandError):
            call_command('mtime_cache')

    def test_handle_add(self):
        out = StringIO()
        with self.settings(CACHES={}):
            call_command(
                'mtime_cache', '--add', *self.default_ignore(), stdout=out)
        output = out.getvalue()
        self.assertIn('Deleted mtimes of 20 files from the cache.', output)
        self.assertIn('Added mtimes of 20 files to cache.', output)

    def test_handle_clean(self):
        out = StringIO()
        with self.settings(CACHES={}):
            call_command(
                'mtime_cache', '--clean', *self.default_ignore(), stdout=out)
        output = out.getvalue()
        self.assertIn('Deleted mtimes of 20 files from the cache.', output)
        self.assertNotIn('Added mtimes of 20 files to cache.', output)
