import sys
import warnings

from django.core.management.base import  NoArgsCommand, CommandError
from optparse import make_option
from django.utils.simplejson.decoder import JSONDecoder
from compressor.offline import compress_offline
from compressor.conf import settings


class Command(NoArgsCommand):
    """Management command to offline generate the django_compressor cache content."""

    option_list = NoArgsCommand.option_list + (
        make_option('-c', '--context', default="", dest='context',
            help="""Context to use while rendering the 'compress' nodes."""
                 """ (In JSON format; e.g.: '{"something": 1, "other": "value"}'"""),
        make_option('-f', '--force', default=False, action="store_true", dest='force',
            help="Force generation of offline cache even if "
                 "settings.COMPRESS and/or settings.COMPRESS_OFFLINE is not set."),
    )

    def handle_noargs(self, **options):
        verbosity = int(options.get("verbosity", 0))

        if not settings.COMPRESS and not options.get("force"):
            raise CommandError(
                "Compressor is disabled. Set COMPRESS settting to True "
                "(or DEBUG to False) to enable. (Use -f to override)")

        if not settings.COMPRESS_OFFLINE:
            if not options.get("force"):
                raise CommandError(
                    "Aborting; COMPRESS_OFFLINE is not set. (Use -f to override)")
            warnings.warn(
                "COMPRESS_OFFLINE is not set. Offline generated cache will not be used.")

        context = None
        if "context" in options and options['context']:
            try:
                context = JSONDecoder().decode(options['context'])
            except ValueError, e:
                raise CommandError("Invalid context JSON specified.", e)

        compress_offline(verbosity, context, sys.stdout)
