class Transaction(object):
    def __init__(self, tid, timestamp, description, amount_pence,
                 category_1=None, category_2=None, category_3=None, notes=None):
        self.tid = tid
        self.timestamp = timestamp
        self.description = description
        self.amount_pence = amount_pence
        self.category_1 = category_1
        self.category_2 = category_2
        self.category_3 = category_3
        self.notes = notes
