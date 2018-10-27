from contextlib import closing
from pysqlcipher3 import dbapi2 as sqlcipher


_SCHEMA_VERSION = 1


class Connection(object):
    def __init__(self, path, key):
        self._path = path
        self._key = key

    def connect(self):
        self.db = sqlcipher.connect(self._path)
        self._do_crypto()

        if not self._is_seeded():
            self._seed()

        self._assert_version()

    def _do_crypto(self):
        with self._safe_cursor() as c:
            c.execute('pragma key="%s";' % self._key)
            c.execute('pragma kdf_iter=64000;')

    def _is_seeded(self):
        try:
            with self._safe_cursor() as c:
                c = self.db.cursor()
                c.execute('SELECT 1 FROM schema')
                return True
        except sqlcipher.OperationalError:
            return False

    def _seed(self):
        with self._safe_cursor() as c:
            c.execute('CREATE TABLE schema (version INTEGER)')
            c.execute('INSERT INTO schema VALUES (?)', (_SCHEMA_VERSION,))
            self.db.commit()

    def _assert_version(self):
        with self._safe_cursor() as c:
            version = c.execute('SELECT * FROM schema').fetchone()[0]
            if version != _SCHEMA_VERSION:
                self.db.close()
                raise SchemaMismatch(_SCHEMA_VERSION, version)

    def _safe_cursor(self):
        return closing(self.db.cursor())


class SchemaMismatch(Exception):
    def __init__(self, expected, actual):
        msg = 'DB schema mismatch. Expected %d; actual %d' % (expected, actual)
        super(SchemaMismatch, self).__init__(msg)


if __name__ == '__main__':
    db = Connection('testing.db', 'apple')
    db.connect()
