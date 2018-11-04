import datetime
import hashlib
from .api import Transaction
from contextlib import closing
from pysqlcipher3 import dbapi2 as sqlcipher


_SCHEMA = (
    ('schema', (
        ('hash', 'TEXT'),
    )),
    ('transactions', (
        ('id', 'INTEGER PRIMARY KEY'),
        ('timestamp', 'TIMESTAMP'),
        ('description', 'TEXT'),
        ('amount_pence', 'INTEGER'),
        ('category_1', 'TEXT'),
        ('category_2', 'TEXT'),
        ('category_3', 'TEXT'),
        ('notes', 'TEXT'),
    )),
)


class Connection(object):
    def __init__(self, path, key):
        self.db = None
        self._path = path
        self._key = key

    def connect(self):
        self.db = sqlcipher.connect(self._path)
        self._do_crypto()

        if not self._is_seeded():
            self._seed()

        self._assert_schema_hash()

    def close(self):
        if self.db is not None:
            self.db.close()

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
            for table, cols in _SCHEMA:
                col_descriptor = ','.join(('%s %s' % col for col in cols))
                c.execute('CREATE TABLE %s (%s)' % (table, col_descriptor))
            c.execute('INSERT INTO schema VALUES (?)', (self._schema_hash(),))
            self.db.commit()

    def _schema_hash(self):
        m = hashlib.md5()
        for table, cols in _SCHEMA:
            m.update(b'#')
            m.update(table.encode('utf-8'))
            for col_name, col_type in cols:
                m.update(b'|')
                m.update(col_name.encode('utf-8'))
                m.update(b'|')
                m.update(col_type.encode('utf-8'))
        return m.hexdigest()

    def _assert_schema_hash(self):
        expected_hash = self._schema_hash()
        c = self.db.cursor()
        success = False
        try:
            db_hash = str(c.execute('SELECT * FROM schema').fetchone()[0])
            if db_hash != expected_hash:
                raise SchemaMismatch(expected_hash, db_hash)
            success = True
        finally:
            c.close()
            if not success:
                self.db.close()

    def _safe_cursor(self):
        return closing(self.db.cursor())

    def store_transactions(self, txs):
        for tx in txs:
            self.store_transaction(tx)

    def store_transaction(self, tx):
        if tx.tid is None:
            self._create_transaction(tx)
        else:
            self._update_transaction(tx)

    def fetch_transactions(self, condition, params):
        with self._safe_cursor() as c:
            query = 'SELECT * from transactions WHERE {}'.format(condition)
            qs = c.execute(query, params)
            for row in qs:
                yield self._deserialize_tx(row)

    def has_transaction(self, tx):
        with self._safe_cursor() as c:
            t_serial = self._serialize_tx(tx)
            q = '''SELECT COUNT(*) from transactions WHERE
                     timestamp=? AND
                     description=? AND
                     amount_pence=?'''
            res = c.execute(q, t_serial[:3]).fetchone()[0]
            assert(res in [0, 1])
            return res == 1

    def select_raw(self, query, params):
        with self._safe_cursor() as c:
            return c.execute(query, params).fetchall()

    def _create_transaction(self, tx):
        if self.has_transaction(tx):
            return

        with self._safe_cursor() as c:
            c.execute("""INSERT INTO transactions
                        (timestamp, description, amount_pence,
                        category_1, category_2, category_3, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      self._serialize_tx(tx))
            self.db.commit()
            tx.tid = c.lastrowid

    def _update_transaction(self, tx):
        assert(self.has_transaction(tx))
        with self._safe_cursor() as c:
            c.execute("""UPDATE transactions
                         SET timestamp=?, description=?, amount_pence=?,
                             category_1=?, category_2=?, category_3=?, notes=?
                         WHERE id=?""",
                      self._serialize_tx(tx) + (tx.tid,))
            assert(c.rowcount == 1)
            self.db.commit()

    def _serialize_tx(self, tx):
        return (_datetime_to_epoch(tx.timestamp),
                tx.description, tx.amount_pence,
                tx.category_1, tx.category_2, tx.category_3,
                tx.notes)

    def _deserialize_tx(self, tx_row):
        tx = Transaction(*tx_row)
        tx.timestamp = _epoch_to_datetime(tx.timestamp)
        return tx

    def filter(self, criterion):
        return View(self, criterion)

    def as_view(self):
        return self.filter(Filter.all())


class View(object):
    def __init__(self, parent, filter_data):
        if isinstance(parent, Connection):
            self.db = parent
            self.filter_str = filter_data[0]
            self.filter_params = filter_data[1]
        elif isinstance(parent, View):
            self.db = parent.db
            self.filter_str = '{} AND {}'.format(parent.filter_str, filter_data[0])
            self.filter_params = parent.filter_params + filter_data[1]
        else:
            raise ValueError('Unexpected type %s', str(parent.__class__))

    def __iter__(self):
        return self.db.fetch_transactions(self.filter_str, self.filter_params)

    def __len__(self):
        try:
            return sum(1 for _ in self)
        except sqlcipher.InterfaceError as e:
            raise Exception('{} with {}'.format(self.filter_str, self.filter_params), e)

    def filter(self, criterion):
        return View(self, criterion)


class Filter(object):
    @staticmethod
    def all():
        return ('1', ())

    @staticmethod
    def description(substr):
        return ('description LIKE "%" || ? || "%"', (substr,))

    @staticmethod
    def category(categories):
        query_parts = ['category_1=?']
        if len(categories) > 1:
            query_parts.append('category_2=?')
        if len(categories) > 2:
            query_parts.append('category_3=?')
        if len(categories) > 3:
            raise ValueError('Invalid category filter "{}" - max 3 categories allowed'.format(categories))
        query = ' AND '.join(query_parts)
        return (query, categories)

    @staticmethod
    def date_range(start_incl, end_incl):
        start_epoch = _datetime_to_epoch(start_incl)
        end_epoch = _datetime_to_epoch(end_incl)
        query = 'timestamp >= ? AND timestamp <= ?'
        return (query, (start_epoch, end_epoch))

    @staticmethod
    def date_before(start_incl):
        start_epoch = _datetime_to_epoch(start_incl)
        return ('timestamp <= ?', (start_epoch,))

    @staticmethod
    def date_after(end_incl):
        end_epoch = _datetime_to_epoch(end_incl)
        return ('timestamp >= ?', (end_epoch,))

    @staticmethod
    def id(tid):
        return ('id = ?', (tid,))

    @staticmethod
    def untagged():
        return ('category_1 IS NULL', tuple())


class SchemaMismatch(Exception):
    def __init__(self, expected, actual):
        msg = 'DB schema mismatch. Expected %s; actual %s' % (expected, actual)
        super(SchemaMismatch, self).__init__(msg)


def _datetime_to_epoch(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return int((dt - epoch).total_seconds() * 1000000)


def _epoch_to_datetime(dt):
    return datetime.datetime.utcfromtimestamp(dt / 1000000)


if __name__ == '__main__':
    db = Connection('testing.db', 'apple')
    db.connect()
