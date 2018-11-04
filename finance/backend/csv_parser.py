import csv
import datetime
import re
from .api import Transaction


def get_csv_transactions(path):
    with open(path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            yield parse_row(row)


def parse_row(row):
    date, description, quantity = row
    date = datetime.datetime.strptime(date, '%d/%m/%Y')
    description = re.sub(' {2,}', ' - ', description)
    quantity = -int(re.sub('[.,]', '', quantity))
    return Transaction(
        None,
        date,
        description,
        quantity,
    )
