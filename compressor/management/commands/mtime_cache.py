import fnmatch
import os
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError

from compressor.cache import cache, get_mtime, get_mtime_cachekey
from compressor.conf import settings
from compressor.utils import walk


class Command(NoArgsCommand):
    help = "Add or remove all mtime values from the cache"
    option_list = NoArgsCommand.option_list + (
        make_option('-i', '--ignore', action='append', default=[],
            dest='ignore_patterns', metavar='PATTERN',
            help="Ignore files or directories matching this glob-style "
                "pattern. Use multiple times to ignore more."),
        make_option('--no-default-ignore', action='store_false',
            dest='use_default_ignore_patterns', default=True,
            help="Don't ignore the common private glob-style patterns 'CVS', "
                "'.*' and '*~'."),
        make_option('--follow-links', dest='follow_links', action='store_true',
            help="Follow symlinks when traversing the COMPRESS_ROOT "
                "(which defaults to MEDIA_ROOT). Be aware that using this "
                "can lead to infinite recursion if a link points to a parent "
                "directory of itself."),
        make_option('-c', '--clean', dest='clean', action='store_true',
            help="Remove all items"),
        make_option('-a', '--add', dest='add', action='store_true',
            help="Add all items"),
    )

    def is_ignored(self, path):
        """
        Return True or False depending on whether the ``path`` should be
        ignored (if it matches any pattern in ``ignore_patterns``).
        """
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatchcase(path, pattern):
                return True
        return False

    def handle_noargs(self, **options):
        ignore_patterns = options['ignore_patterns']
        if options['use_default_ignore_patterns']:
            ignore_patterns += ['CVS', '.*', '*~']
            options['ignore_patterns'] = ignore_patterns
        self.ignore_patterns = ignore_patterns

        if (options['add'] and options['clean']) or (not options['add'] and not options['clean']):
            raise CommandError('Please specify either "--add" or "--clean"')

        if not settings.COMPRESS_MTIME_DELAY:
            raise CommandError('mtime caching is currently disabled. Please '
                'set the COMPRESS_MTIME_DELAY setting to a number of seconds.')

        files_to_add = set()
        keys_to_delete = set()

        for root, dirs, files in walk(settings.COMPRESS_ROOT, followlinks=options['follow_links']):
            for dir_ in dirs:
                if self.is_ignored(dir_):
                    dirs.remove(dir_)
            for filename in files:
                common = "".join(root.split(settings.COMPRESS_ROOT))
                if common.startswith(os.sep):
                    common = common[len(os.sep):]
                if self.is_ignored(os.path.join(common, filename)):
                    continue
                filename = os.path.join(root, filename)
                keys_to_delete.add(get_mtime_cachekey(filename))
                if options['add']:
                    files_to_add.add(filename)

        if keys_to_delete:
            cache.delete_many(list(keys_to_delete))
            print "Deleted mtimes of %d files from the cache." % len(keys_to_delete)

        if files_to_add:
            for filename in files_to_add:
                get_mtime(filename)
            print "Added mtimes of %d files to cache." % len(files_to_add)
