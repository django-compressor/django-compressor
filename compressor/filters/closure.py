import base64
import json
import os
from django.core.files.temp import NamedTemporaryFile
import io
from compressor.conf import settings
from compressor.filters import CompilerFilter
from compressor.exceptions import FilterError


class ClosureCompilerFilter(CompilerFilter):
    command = "{binary} {args}"
    options = (
        ("binary", settings.COMPRESS_CLOSURE_COMPILER_BINARY),
        ("args", settings.COMPRESS_CLOSURE_COMPILER_ARGUMENTS),
    )
    minfile = None

    def __init__(self, content, **kwargs):
        super(ClosureCompilerFilter, self).__init__(content, **kwargs)

        if settings.COMPRESS_CLOSURE_COMPILER_SOURCEMAPS and not settings.COMPRESS_OFFLINE_GROUP_FILES:
            self.command = self.command.replace('{args}', '--create_source_map {mapfile} {args}')

    def input(self, **kwargs):
        encoding = self.default_encoding
        options = dict(self.options)

        if "{mapfile}" in self.command and "mapfile" not in options:
            # create temporary mapfile file if needed
            ext = self.type and ".%s.map" % self.type or ""
            self.minfile = NamedTemporaryFile(mode='r+', suffix=ext)
            options["mapfile"] = self.minfile.name

        self.options = options

        filtered = super(ClosureCompilerFilter, self).input(**kwargs)

        try:
            mapfile_path = options.get('mapfile')
            if mapfile_path:
                with io.open(mapfile_path, 'r', encoding=encoding) as file:
                    map = file.read()

                map_dict = json.loads(map)
                sources = map_dict['sources']
                sources[sources.index('stdin')] = kwargs['elem']['attrs_dict']['src']
                map_dict['file'] = os.path.basename(kwargs['elem']['attrs_dict']['src'])
                map_dict['sources'] = sources
                map = json.dumps(map_dict)

                filtered = '%s\n//# sourceMappingURL=data:application/json;base64,%s' % (
                    filtered,
                    base64.standard_b64encode(map)
                )
        except (IOError, OSError) as e:
            raise FilterError('Unable add source map %s (%r): %s' %
                              (self.__class__.__name__, self.command, e))
        finally:
            if self.minfile is not None:
                self.minfile.close()
        return filtered
