from .db import Connection


class View(object):
    def __init__(self, parent, filter_data):
        if isinstance(parent, Connection):
            self.db = parent
            self.filter_str = filter_data[0]
            self.filter_params = filter_data[1]
        elif isinstance(parent, View):
            self.db = parent.db
            self.filter_str = '%s AND %s' % (parent.filter_str, filter_data[0])
            self.filter_params = parent.filter_params + filter_data[1]
        else:
            raise ValueError('Unexpected type %s', str(parent.__class__))

    def __iter__(self):
        return self.db.fetch_transactions(self.filter_str, self.filter_params)

    def __len__(self):
        return sum(1 for _ in self)


class Filter(object):
    ALL = ('1', ())
