import datetime
import os
import unittest
from contextlib import closing
from .api import Transaction
from .db import Connection, Filter


class TestDb(unittest.TestCase):
    def test_init_succeeds(self):
        in_memory_db()

    def test_db_is_seeded(self):
        with in_memory_db() as db:
            with db._safe_cursor() as c:
                c.execute('SELECT 1 FROM schema')
                c.execute('SELECT 1 FROM transactions')

    def test_write(self):
        with in_memory_db() as db:
            db.connect()
            with db._safe_cursor() as c:
                c.execute('CREATE TABLE testtable(data TEXT)')
                c.execute('INSERT INTO testtable VALUES ("swordfish")')
                result = c.execute('SELECT * FROM testtable').fetchone()[0]
                self.assertEqual('swordfish', result)

    def test_db_can_be_reopened(self):
        try:
            with new_db('unittest.db', 'password') as db:
                with db._safe_cursor() as c:
                    c.execute('CREATE TABLE testtable(data TEXT)')
                    c.execute('INSERT INTO testtable VALUES ("rosebud")')
                    db.db.commit()
            with new_db('unittest.db', 'password') as db:
                with db._safe_cursor() as c:
                    result = c.execute('SELECT * FROM testtable').fetchone()[0]
                    self.assertEqual('rosebud', result)
        finally:
            os.remove('unittest.db')

    def test_invalid_passwords_are_rejected(self):
        try:
            with new_db('unittest.db', 'password') as db:
                with db._safe_cursor() as c:
                    c.execute('CREATE TABLE testtable(data TEXT)')
                    db.db.commit()
            db = Connection('unittest.db', 'incorrect_password')
            self.assertRaises(Exception, lambda: db.connect())
        finally:
            os.remove('unittest.db')


class TestSchema(unittest.TestCase):
    def test_persist_and_retrieve_transaction(self):
        with in_memory_db() as db:
            now = datetime.datetime.now()
            tx = Transaction(None, now, "Test tx", 123456, "a", "b", "c", "note")
            db.store_transaction(tx)
            tx2 = next(db.fetch_transactions("1", ()))
            self.assertEqual(tx.timestamp, tx2.timestamp)
            self.assertEqual(tx.description, tx2.description)
            self.assertEqual(tx.amount_pence, tx2.amount_pence)
            self.assertEqual(tx.category_1, tx2.category_1)
            self.assertEqual(tx.category_2, tx2.category_2)
            self.assertEqual(tx.category_3, tx2.category_3)
            self.assertEqual(tx.notes, tx2.notes)

    def test_transaction_id_set_on_save(self):
        with in_memory_db() as db:
            tx = Transaction(None, datetime.datetime.now(), "", 0, "", "", "", "")
            self.assertIsNone(tx.tid)
            db.store_transaction(tx)
            self.assertIsNotNone(tx.tid)
            stored_id = next(db.fetch_transactions("1", ())).tid
            self.assertEqual(tx.tid, stored_id)


class TestViews(unittest.TestCase):
    _TRANSACTIONS = [
        ('2018-01-04 13:00', '490', 'Panini Paradise', 'Food', 'Snack', '', 'Delicious'),
        ('2018-01-04 20:00', '3100', 'Generico Supermarket', 'Food', 'Groceries', '', ''),
        ('2018-01-05 13:20', '490', 'Panini Paradise', '', '', '', ''),
    ]

    def setUp(self):
        self.db = Connection(':memory:', 'password')
        self.db.connect()
        for tx_data in TestViews._TRANSACTIONS:
            tx_data = list(tx_data)
            tx_data[0] = datetime.datetime.strptime(tx_data[0], '%Y-%m-%d %H:%M')
            tx_data[1], tx_data[2] = tx_data[2], tx_data[1]
            tx_data = [None] + tx_data
            tx = Transaction(*tuple(tx_data))
            self.db.store_transaction(tx)

    def tearDown(self):
        self.db.close()

    def test_all_filter(self):
        v = self.db.filter(Filter.all())
        self.assertEqual(len(TestViews._TRANSACTIONS), len(v))

    def test_description_contains(self):
        v = self.db.filter(Filter.description_contains('Panini'))
        self.assertEqual(2, len(v))


def new_db(path, key):
    db = Connection(path, key)
    db.connect()
    return closing(db)


def in_memory_db():
    return new_db(':memory:', 'password')


if __name__ == '__main__':
    unittest.main()
