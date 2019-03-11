from curses import wrapper
import datetime
import logging.config
import os
import sys
from getpass import getpass
from .backend import Connection, Transaction, get_csv_transactions, get_pdf_transactions
from .frontend import Ui


logger = logging.getLogger(__name__)


def init_logging():
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
    logging.config.fileConfig(log_file_path, disable_existing_loggers=False)
    logger.info("Finance starting up - logging initialized")


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
    init_logging()
    logger.info("Starting REPL environment")
    db_file = sys.argv[1]
    key = getpass('Password: ')
    db = Connection(db_file, key)
    db.connect()
    if len(db.as_view()) == 0:
        add_test_data(db)
    ui = Ui(db)
    wrapper(ui.run)


def ingest_file():
    init_logging()
    db_file, path = sys.argv[1:]
    logger.info("Starting file ingest for file at '%s'", path)
    key = getpass('Password: ')
    db = Connection(db_file, key)
    db.connect()

    if path.endswith('.csv'):
        logger.info("Performing CSV import")
        txs = get_csv_transactions(path)
        logger.info("Imported %d transactions", len(txs))
    elif path.endswith('.pdf'):
        logger.info("Performing PDF import")
        txs = get_pdf_transactions(path)
        logger.info("Imported %d transactions", len(txs))
    else:
        raise ValueError("Unsupported file type")

    for tx in txs:
        db.store_transaction(tx)
    log.info("Stored %d transactions successfully", len(txs))


if __name__ == '__main__':
    repl()
