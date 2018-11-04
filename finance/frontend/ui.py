import curses
import textwrap


class Ui(object):
    def __init__(self):
        self.screen = None
        self.title_win = None
        self.display_pad = None
        self.input_win = None
        self.input_buffer = ''
        self.cursor_offset = 0

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

        display_window = curses.newwin(display_height, max_width, title_height, 0)
        self.display_pad = ViewPane(display_window)
        self.display_pad.repaint()

        self.input_win = InputPane(0, title_height + display_height, max_width, input_height)
        self.input_win.repaint()

        curses.curs_set(0)

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
            self.display_pad.scroll_up(1)
        elif c == curses.KEY_DOWN:
            self.display_pad.scroll_down(1)
        elif c == curses.KEY_ENTER or c == 10 or c == 13:
            command = self.input_win.flush_buffer()
            self.display_pad.reset_scroll()
            should_continue = self.handle_command(command)
        else:
            return False

        self.input_win.repaint()
        return should_continue

    def handle_command(self, command):
        cmd = command.lower().strip()
        if cmd == 'exit':
            return False
        elif len(cmd) == 0:
            self.display_pad.write_line(' ')
        else:
            self.display_pad.write_line('Cannot parse command: {}'.format(command))
        return True


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
        self.buffer = self.buffer[:self.cursor_pos - 1] + self.buffer[self.cursor_pos:]
        self.cursor_pos -= 1

    def flush_buffer(self):
        flushed = self.buffer
        self.buffer = ''
        self.cursor_pos = 0
        return flushed


class ViewPane(object):
    def __init__(self, window):
        self.window = window
        self.lines = []
        self.scrollback = []
        self.height, self.width = window.getmaxyx()
        self.scroll = 0
        self.max_scroll = 0

    def repaint(self):
        self.window.clear()
        frame_start = self.scroll - self.height + 1
        frame_end = self.scroll
        if frame_start < 0:
            padding = -1 * frame_start
            frame_start = 0
        else:
            padding = 0

        frame = self.scrollback[frame_start:frame_end]

        for idx, line in enumerate(frame):
            self.window.addstr(padding + idx, 0, line)
        self.window.refresh()

    def rebind(self, window):
        self.window.clear()
        self.window.refresh()
        window.clear()

        self.window = window
        self.height, self.width = window.getmaxyx()

        lines = self.lines
        self.lines, self.scrollback = [], []
        self.scroll, self.max_scroll = 0, 0
        self.write_lines(lines)

    def render_line(self, line):
        lines = textwrap.wrap(line, width=curses.COLS)
        if len(lines) != 1:
            # If the line got wrapped, or was blank, append an extra newline
            lines += ['']
        return lines

    def write_line(self, line):
        self.write_lines([line])

    def write_lines(self, lines):
        self.lines.extend(lines)
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


if __name__ == '__main__':
    ui = Ui()
    curses.wrapper(ui.run)
