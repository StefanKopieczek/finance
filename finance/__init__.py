if __package__ is None or __package__ == '':
    from frontend import Ui
    from backend import Connection, Transaction
else:
    from .frontend import Ui
    from .backend import Connection, Transaction
