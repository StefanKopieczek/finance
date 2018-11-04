import curses
import textwrap
import time
from collections import defaultdict
from ..backend import Filter


class Ui(object):
    def __init__(self, db):
        self.db = db
        self.screen = None
        self.title_win = None
        self.view_panes = []
        self.input_win = None
        self.display_area = None

    def run(self, stdscr):
        self.screen = stdscr
        self.init_ui()
        while self.handle_input():
            pass

    def init_ui(self):
        self.screen.refresh()
        max_width = curses.COLS
        max_height = curses.LINES

        title_height = int(max_height * 0.1)
        input_height = int((max_height - title_height) * 0.10)
        display_height = max_height - (title_height + input_height)

        title_win = curses.newwin(title_height, max_width, 0, 0)
        title_str = "STEFAN'S PATENTED FINANCIAL PLANNER"
        title_x = int(max_width / 2 - len(title_str) / 2)
        title_win.border(0, 0, 0, 0)
        title_win.addstr(1, title_x, "STEFAN'S PATENTED FINANCIAL PLANNER", curses.A_BOLD + curses.A_UNDERLINE)
        title_win.refresh()
        self.title_win = title_win

        self.display_area = (0, title_height, max_width, display_height)
        self.refresh_view_panes([self.db.as_view()])

        self.input_win = InputPane(0, title_height + display_height, max_width, input_height)
        self.input_win.repaint()

        curses.curs_set(0)

    def refresh_view_panes(self, db_contexts):
        # Hide existing view panes
        for view_pane in self.view_panes:
            view_pane.rebind(None)

        # Create new view panes
        x0, y0, total_width, height = self.display_area
        window_width = int(total_width / len(db_contexts))
        self.view_panes = []
        for idx, db_context in enumerate(db_contexts):
            window = curses.newwin(height, window_width, y0, x0 + window_width * idx)
            view_pane = ViewPane(window, db_context)
            view_pane.repaint()
            self.view_panes.append(view_pane)

    def handle_input(self):
        should_continue = True
        c = self.screen.getch()
        if 32 <= c <= 126:
            self.input_win.add_char(c)
        elif c == curses.KEY_LEFT:
            self.input_win.move_cursor_left()
        elif c == curses.KEY_RIGHT:
            self.input_win.move_cursor_right()
        elif c == curses.KEY_BACKSPACE:
            self.input_win.backspace()
        elif c == curses.KEY_UP:
            for pane in self.view_panes:
                pane.scroll_up(1)
            time.sleep(0.05)
            curses.flushinp()
        elif c == curses.KEY_DOWN:
            for pane in self.view_panes:
                pane.scroll_down(1)
            time.sleep(0.05)
            curses.flushinp()
        elif c == curses.KEY_ENTER or c == 10 or c == 13:
            command = self.input_win.flush_buffer()
            for pane in self.view_panes:
                pane.reset_scroll()
            should_continue = self.handle_command(command)
        else:
            return False

        self.input_win.repaint()
        return should_continue

    def handle_command(self, command):
        cmd = command.lower().strip()
        is_handled, continue_running = self.handle_global_command(cmd)
        if not is_handled:
            for pane in self.view_panes:
                pane.handle_command(cmd)

        return continue_running

    def handle_global_command(self, command):
        if command == 'exit' or command == 'quit':
            return True, False
        else:
            return False, True


class InputPane(object):
    INDENT = 4

    def __init__(self, x0, y0, width, height):
        self.window = curses.newwin(height, width, y0, x0)
        self.buffer = ''
        self.cursor_pos = 0

    def repaint(self):
        w = self.window
        w.clear()
        w.border(' ', ' ', curses.ACS_HLINE, ' ')
        start = InputPane.INDENT
        w.addstr(1, start, '>', curses.A_BOLD)
        w.addstr(1, start + 2, self.buffer[:self.cursor_pos])
        w.addstr(1, start + 2 + self.cursor_pos, '_', curses.A_BLINK)
        w.addstr(1, start + 2 + self.cursor_pos + 1, self.buffer[self.cursor_pos:])
        w.refresh()

    def add_char(self, c):
        self.buffer = self.buffer[:self.cursor_pos] + chr(c) + self.buffer[self.cursor_pos:]
        self.cursor_pos += 1

    def move_cursor_left(self):
        if self.cursor_pos >= 0:
            self.cursor_pos -= 1
        else:
            curses.beep()

    def move_cursor_right(self):
        if self.cursor_pos < len(self.buffer):
            self.cursor_pos += 1
        else:
            curses.beep()

    def backspace(self):
        if self.cursor_pos > 0:
            self.buffer = self.buffer[:self.cursor_pos - 1] + self.buffer[self.cursor_pos:]
            self.cursor_pos -= 1

    def flush_buffer(self):
        flushed = self.buffer
        self.buffer = ''
        self.cursor_pos = 0
        return flushed


class ViewPane(object):
    def __init__(self, window, db_context):
        self.window = window
        self.lines = []
        self.scrollback = []
        self.scroll = 0
        self.max_scroll = 0
        self.db_context = db_context
        self.original_db_context = db_context

    def repaint(self):
        if self.window is not None:
            height, _ = self.window.getmaxyx()
            self.window.clear()
            self.window.border(0, 0, ' ', ' ')
            frame_start = self.scroll - height + 1
            frame_end = self.scroll
            if frame_start < 0:
                padding = -1 * frame_start
                frame_start = 0
            else:
                padding = 0

            frame = self.scrollback[frame_start:frame_end]

            for idx, line in enumerate(frame):
                self.window.addstr(padding + idx, 2, line)
            self.window.refresh()

    def rebind(self, window):
        if self.window is not None:
            self.window.clear()
            self.window.refresh()

        if window is not None:
            window.clear()

        self.window = window
        lines = self.lines
        self.lines, self.scrollback = [], []
        self.scroll, self.max_scroll = 0, 0
        self.write_lines(lines)

    def render_line(self, line):
        _, area_width = self.window.getmaxyx()
        border_width = 4
        actual_width = area_width - border_width
        lines = textwrap.wrap(line, width=actual_width)
        if len(lines) != 1:
            # If the line got wrapped, or was blank, append an extra newline
            lines += ['']
        return lines

    def write_line(self, line):
        self.write_lines([line])

    def write_lines(self, lines):
        self.lines.extend(lines)
        if self.window is not None:
            for line in lines:
                rendered_lines = self.render_line(line)
                self.scrollback.extend(rendered_lines)
                to_scroll = len(rendered_lines)
                self.max_scroll += to_scroll
                self.scroll += to_scroll
            self.repaint()

    def scroll_down(self, num_lines):
        self.scroll = min(self.max_scroll, self.scroll + num_lines)
        self.repaint()

    def scroll_up(self, num_lines):
        self.scroll = max(1, self.scroll - num_lines)
        self.repaint()

    def reset_scroll(self):
        self.scroll = self.max_scroll
        self.repaint()

    def handle_command(self, command):
        if len(command) == 0:
            self.write_line(' ')
            return

        self.write_line('> {}'.format(command))
        if command == 'list':
            self.list_transactions(self.db_context)
        elif command == 'tags':
            tags = self.db_context.db.select_raw('''SELECT DISTINCT
                                                    category_1, category_2, category_3
                                                    FROM transactions''', tuple())
            lines = sorted([format_category(tag) for tag in tags])
            lines.append('')
            self.write_lines(lines)
        elif command.startswith('tag all'):
            _, _, *categories = command.split() # noqa
            if len(categories) > 3:
                self.write_line('ERROR: At most 3 categories permitted')
                return

            count = len(self.db_context)
            tag = format_category(categories)
            if len(categories) < 3:
                categories.extend([None] * (3 - len(categories)))
            for tx in self.db_context:
                tx.category_1, tx.category_2, tx.category_3 = categories
                self.db_context.db.store_transaction(tx)
            self.write_line('Updated {} transactions'.format(count))
        elif command.startswith('tag'):
            parts = command.split()
            if len(parts) == 1:
                self.write_line('ERROR: Transaction ID required')
                return

            _, tid, *categories = parts # noqa
            if len(categories) > 3:
                self.write_line('ERROR: At most 3 categories permitted')
                return

            matches = list(self.db_context.db.fetch_transactions('id=?', (tid,)))
            if len(matches) == 0:
                self.write_line('ERROR: Transaction #{} not found'.format(tid))
            else:
                tx = matches[0]
                if len(categories) < 3:
                    categories.extend([None] * (3 - len(categories)))
                tx.category_1, tx.category_2, tx.category_3 = categories
                self.db_context.db.store_transaction(tx)
        elif command == 'filter untagged':
            self.db_context = self.db_context.filter(Filter.untagged())
            self.print_filter_status()
        elif command.startswith('filter \"') or command.startswith('filter \''):
            _, term = command.split(maxsplit=1)
            if len(term) == 1 or term[0] != term[-1]:
                self.write_line('ERROR: Invalid term {}', term)
                return
            else:
                term = term[1:-1]
                self.db_context = self.db_context.filter(Filter.description(term))
                self.print_filter_status()
        elif command == 'summary':
            self.summary()
        elif command == 'reset':
            self.db_context = self.original_db_context
            self.write_line('=> Showing {} total transactions'.format(len(self.db_context)))
        else:
            self.write_line('Cannot parse command: {}'.format(command))

    def list_transactions(self, txs):
        lines = list(format_transactions(txs))
        lines.append('--- {} transactions ---'.format(len(lines)))
        lines.append('')
        self.write_lines(lines)

    def print_filter_status(self):
        self.write_line('=> Filtered down to {} transactions'.format(len(self.db_context)))

    def summary(self):
        txs = list(self.db_context)
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
        self.write_lines(lines)


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


if __name__ == '__main__':
    ui = Ui(None)
    curses.wrapper(ui.run)
