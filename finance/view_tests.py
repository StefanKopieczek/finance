import unittest
from .api import Transaction
from .db import Connection
from .views import View, Filter

_TRANSACTIONS = []


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.db = Connection(':memory:', 'password')
        self.db.connect()
        for tx_data in _TRANSACTIONS:
            tx_data[1], tx_data[2] = tx_data[2], tx_data[1]
            tx = Transaction(*tx_data)
            self.db.store_transaction(tx)

    def tearDown(self):
        self.db.close()

    def test_all_filter(self):
        v = View(self.db, Filter.ALL)
        self.assertEqual(len(_TRANSACTIONS), len(v))


if __name__ == '__main__':
    unittest.main()
