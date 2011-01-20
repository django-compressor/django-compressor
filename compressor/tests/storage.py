import gzip
from compressor.storage import CompressorFileStorage


class TestStorage(CompressorFileStorage):
    """
    Test compressor storage that gzips storage files
    """
    def url(self, name):
        return u'%s.gz' % super(TestStorage, self).url(name)

    def save(self, filename, content):
        filename = super(TestStorage, self).save(filename, content)
        out = gzip.open(u'%s.gz' % self.path(filename), 'wb')
        out.writelines(open(self.path(filename), 'rb'))
        out.close()
