from optparse import make_option
import os

from django.core.cache import cache
from django.core.management.base import NoArgsCommand, CommandError

from compressor.conf import settings
from compressor.utils import get_mtime

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--ignore-vcs', dest='ignore_vcs', action='store_true', help="Don't traverse into VCS directories"),
        make_option('--follow-links', dest='follow_links', action='store_true', help='Follow symlinks when traversing the `COMPRESS_ROOT` (default `MEDIA_ROOT`). '
        'Be aware that setting follow-links can lead to infinite recursion if a link points to a parent directory of itself.'),
        make_option('--clean', dest='clean', action='store_true', help='Remove all items'),
        make_option('--add', dest='add', action='store_true', help='Add all items'),
    )
    help = 'Add or remove all mtimes from the cache'

    def handle_noargs(self, **options):
        if (options['add'] and options['clean']) or (not options['add'] and not options['clean']):
            raise CommandError, 'Please specify either "--add" or "--clean"'

        for root,dirs,files in os.walk(settings.MEDIA_ROOT, followlinks=options['follow_links']):
            if options['ignore_vcs']:
                # no VCS (CVS, SVN, git, hg) directories
                if 'CVS' in dirs:
                    dirs.remove('CVS')
                if '.svn' in dirs:
                    dirs.remove('.svn')
                if '.git' in dirs:
                    dirs.remove('.git')
                if '.hg' in dirs:
                    dirs.remove('.hg')
            for filename in files:
                filename = os.path.join(root,filename)
                key = "django_compressor.mtime.%s" % filename
                cache.set(key, None, 10)
                if options['add']:
                    get_mtime(filename)

