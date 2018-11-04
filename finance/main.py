from curses import wrapper
import datetime
import sys
from getpass import getpass
from .backend import Connection, Transaction, get_transactions
from .frontend import Ui


def add_test_data(db):
    _TRANSACTIONS = [
        ('2018-01-04 13:00', '490', 'Panini Paradise', 'Food', 'Snack', None, 'Delicious'),
        ('2018-01-04 20:00', '3100', 'Generico Supermarket', 'Food', 'Groceries', None, None),
        ('2018-01-05 13:20', '490', 'Panini Paradise', None, None, None, None),
        ('2018-01-06 21:00', '799', 'Webflix', 'Entertainment', 'Movies', 'Streaming', None),
        ('2018-01-07 15:00', '6249', 'Generico Supermarket', 'Food', 'Groceries', 'Occasion', None),
    ]

    for tx_data in _TRANSACTIONS:
        tx_data = list(tx_data)
        tx_data[0] = datetime.datetime.strptime(tx_data[0], '%Y-%m-%d %H:%M')
        tx_data[1], tx_data[2] = tx_data[2], tx_data[1]
        tx_data = [None] + tx_data
        tx = Transaction(*tuple(tx_data))
        db.store_transaction(tx)


def repl():
    db_file = sys.argv[1]
    key = getpass('Password: ')
    db = Connection(db_file, key)
    db.connect()
    if len(db.as_view()) == 0:
        add_test_data(db)
    ui = Ui(db)
    wrapper(ui.run)


def ingest_csv():
    db_file, csvpath = sys.argv[1:]
    key = getpass('Password: ')
    db = Connection(db_file, key)
    db.connect()
    for tx in get_transactions(csvpath):
        db.store_transaction(tx)


if __name__ == '__main__':
    repl()
