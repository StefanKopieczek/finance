import curses
import logging
import textwrap
import time
from .commands import commands


logger = logging.getLogger(__name__)


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
        logger.info("Exiting program")

    def init_ui(self):
        logger.info("Initializing UI")
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
        elif c == curses.KEY_BACKSPACE or c == 127:
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

        self.input_win.repaint()
        return should_continue

    def handle_command(self, command):
        logger.info("Command given: '%s'", command)
        cmd = command.lower().strip()
        is_handled, continue_running = self.handle_global_command(cmd)
        if not is_handled:
            logger.info("Delegating command to %d view panes (%s)", len(self.view_panes), command)
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
        w.erase()
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
            logger.debug("Cursor left requested when cursor is already at leftmost point")
            curses.beep()

    def move_cursor_right(self):
        if self.cursor_pos < len(self.buffer):
            self.cursor_pos += 1
        else:
            logger.debug("Cursor right requested when cursor is already at rightmost point")
            curses.beep()

    def backspace(self):
        if self.cursor_pos > 0:
            self.buffer = self.buffer[:self.cursor_pos - 1] + self.buffer[self.cursor_pos:]
            self.cursor_pos -= 1
        else:
            logger.debug("Cursor backspace requested when cursor is already at leftmost point")

    def flush_buffer(self):
        logger.debug("Flushed buffer")
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
        self.commands = self.register_commands()

    def register_commands(self):
        return {
            'list': commands.show_all,
            'tags': commands.list_tags,
            'tag all': commands.tag_all,
            'tag': commands.tag,
            'filter untagged': commands.filter_untagged,
            'filter tag': commands.filter_tag,
            'filter': commands.filter_text,
            'summary': commands.summary,
            'reset': commands.reset,
        }

    def repaint(self):
        if self.window is not None:
            height, _ = self.window.getmaxyx()
            self.window.erase()
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
        logger.info("Rebinding ViewPane '%r' to window '%r'", self, window)
        if self.window is not None:
            self.window.erase()
            self.window.refresh()

        if window is not None:
            window.erase()

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
        logger.debug("Writing %d lines to ViewPane '%r'", len(lines), self)
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

        logger.debug("ViewPane '%r' executing command '%s'", self, command)

        self.write_line('> {}'.format(command))
        for key, command_func in self.commands.items():
            if command.startswith(key):
                args_string = command[len(key):]
                args = args_string.split()
                output = command_func(self, *args)
                self.write_lines(output)
                break
        else:
            self.write_line('Cannot parse command: {}'.format(command))


if __name__ == '__main__':
    ui = Ui(None)
    curses.wrapper(ui.run)
