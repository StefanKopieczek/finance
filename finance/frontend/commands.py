from collections import defaultdict
from ..backend import Filter


# Can't figure out for the life of me how to import a sibling python file
# into its own namespace, so I'm creating a gross wrapper object to simulate
# it, allowing the UI code to reference e.g. 'commands.tag'.
# This is sad and I am sorry.
# Note that we have to init it at the end of the file so all definitions are ready.
commands = None


def _show_all(view):
    txs = sorted(view.db_context, key=lambda tx: tx.timestamp)
    lines = list(format_transactions(txs))
    lines.append('--- {} transactions ---'.format(len(lines)))
    lines.append('')
    return lines


def _list_tags(view):
    tags = view.db_context.db.select_raw('''SELECT DISTINCT category_1, category_2, category_3 FROM transactions''', tuple())
    lines = sorted([format_category(tag) for tag in tags])
    lines.append('')
    return lines


def _tag_all(view, *categories):
    categories = list(categories)
    count = len(view.db_context)
    tag = format_category(categories)
    if len(categories) < 3:
        categories.extend([None] * (3 - len(categories)))

    txs = list(view.db_context)  # Read all the transactions first to avoid modifying while iterating
    for tx in txs:
        tx.category_1, tx.category_2, tx.category_3 = categories
        view.db_context.db.store_transaction(tx)

    return ['Updated {} transactions'.format(count)]


def _tag(view, tid, *categories):
    categories = list(categories)
    matches = list(view.db_context.db.fetch_transactions('id=?', (tid,)))
    if len(matches) == 0:
        return ['ERROR: Transaction #{} not found'.format(tid)]
    else:
        tx = matches[0]
        if len(categories) < 3:
            categories.extend([None] * (3 - len(categories)))
        tx.category_1, tx.category_2, tx.category_3 = categories
        view.db_context.db.store_transaction(tx)
        return []


def _filter_untagged(view):
    view.db_context = view.db_context.filter(Filter.untagged())
    return get_filter_status(view.db_context)


def _filter_tag(view, *tag):
    view.db_context = view.db_context.filter(Filter.category(tuple(tags)))
    return get_filter_status(view.db_context)


def _filter_text(view, term):
    view.db_context = view.db_context.filter(Filter.description(term))
    return get_filter_status(view.db_context)


def _summary(view):
    txs = list(view.db_context)
    split_idx = 1
    for field in ['category_1', 'category_2', 'category_3']:
        distinct_values = set(getattr(tx, field) for tx in txs)
        if len(distinct_values) > 1:
            break
        split_idx += 1

    summary = defaultdict(int)
    for tx in txs:
        category = format_category([tx.category_1, tx.category_2, tx.category_3][:split_idx])
        summary[category] += tx.amount_pence

    category_size = max(len(c) for c in summary)
    lines = []
    for category in sorted(summary):
        lines.append('{}  {}'.format(
            category.ljust(category_size),
            format_sum(summary[category]),
        ))
    lines.append('')
    return lines


def _reset(view):
    view.db_context = view.original_db_context
    return [
        '=> Showing {} total transactions'.format(len(view.db_context)),
        ''
    ]


def format_category(category_tuple):
    category_parts = []
    for cat in category_tuple:
        if cat is None:
            break
        else:
            category_parts.append(cat)
    category_string = ' > '.join(category_parts)
    if len(category_string) == 0:
        category_string = '[UNTAGGED]'
    return category_string


def format_transaction(transaction):
    category_string = format_category((transaction.category_1, transaction.category_2, transaction.category_3))

    return (
        str(transaction.tid),
        transaction.timestamp.strftime('%Y-%m-%d %H:%H'),
        format_sum(transaction.amount_pence),
        transaction.description,
        category_string,
    )


def format_transactions(txs):
    if len(txs) == 0:
        return []

    tx_rows = [format_transaction(t) for t in txs]
    col_lengths = []
    for idx in range(len(tx_rows[0])):
        col_lengths.append(max(len(row[idx]) for row in tx_rows))

    results = []
    for row in tx_rows:
        padded_cols = []
        for idx, part in enumerate(row):
            padded_cols.append(part.ljust(col_lengths[idx]))
        results.append('  '.join(padded_cols))

    return results


def format_sum(quantity):
    if quantity > 0:
        currency = '£'
    else:
        currency = '-£'
        quantity *= -1

    return '{}{:.2f}'.format(currency, quantity / 100)


def get_filter_status(db_context):
    return [
        '=> Filtered down to {} transactions'.format(len(db_context)),
        ''
    ]


class Command(object):
    def __init__(self, min_args_incl, max_args_excl, f):
        self.min_args_incl = min_args_incl
        self.max_args_excl = max_args_excl
        self.f = f

    def __call__(self, *args, **kwargs):
        if len(kwargs) > 0:
            raise Exception("Programmer error - commands should not be passed kwargs")
        elif len(args) == 0:
            raise Exception("Programmer error - no dbview passed to Command call")
        elif len(args) < self.min_args_incl + 1 or len(args) >= self.max_args_excl  + 1:
            # The 1 offset is because we're passed the calling View, but the user is unaware of
            # this so we shouldn't surface it in the error.
            return ["Invalid command - number of arguments should be in the range {} <= x < {}".format(self.min_args_incl, self.max_args_excl), ""]
        else:
            return self.f(*args)


class Commands(object):
    def __init__(self):
        self.show_all = Command(0, 1, _show_all)
        self.list_tags = Command(0, 1, _list_tags)
        self.tag_all = Command(1, 4, _tag_all)
        self.tag = Command(2, 5, _tag)
        self.filter_untagged = Command(0, 1, _filter_untagged)
        self.filter_tag = Command(1, 4, _filter_tag)
        self.filter_text = Command(1, 2, _filter_text)
        self.summary = Command(0, 1, _summary)
        self.reset = Command(0, 1, _reset)
commands = Commands()
