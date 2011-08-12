import tempfile
from os import path

from compressor.conf import settings
from compressor.filters import CompilerFilter


class CompassFilter(CompilerFilter):
    """
    Converts Compass files to css.
    """
    command = "{binary} compile --force --quiet --boring {args} "
    options = (
        ("binary", settings.COMPRESS_COMPASS_BINARY),
        ("args", settings.COMPRESS_COMPASS_ARGUMENTS),
    )

    def input(self, *args, **kwargs):
        if self.filename is None:
            self.filename = kwargs.pop('filename')
        if not (self.filename.lower().endswith('scss') or
                self.filename.lower().endswith('sass')):
            return ''
        tmpdir = tempfile.mkdtemp()
        parentdir = path.abspath(path.dirname(self.filename))
        self.cwd = path.dirname(parentdir)
        self.infile = open(self.filename)
        outfile_name = path.splitext(path.split(self.filename)[1])[0] + '.css'
        self.options += (
            ('infile', self.filename),
            ('tmpdir', tmpdir),
            ('sassdir', parentdir),
            ('outfile', path.join(tmpdir, outfile_name)),
            ('imagesdir', settings.COMPRESS_COMPASS_IMAGES_DIR),
        )
        for plugin in settings.COMPRESS_COMPASS_PLUGINS:
            self.command += ' --require %s' % plugin
        self.command += (' --sass-dir {sassdir} --css-dir {tmpdir}'
                         ' --images-dir {imagesdir} {infile}')
        return super(CompassFilter, self).input(*args, **kwargs)
