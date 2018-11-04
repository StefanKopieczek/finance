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

        self.display_pad = ViewPane()
        self.display_pad.init_pad(0, title_height, max_width, display_height)

        self.input_win = curses.newwin(input_height, max_width, title_height + display_height, 0)
        self.repaint_input_win()

        curses.curs_set(0)

    def handle_input(self):
        should_continue = True
        c = self.screen.getch()
        if 32 <= c <= 126:
            self.input_buffer = self.input_buffer[:self.cursor_offset] + chr(c) + self.input_buffer[self.cursor_offset:]
            self.cursor_offset += 1
        elif c == curses.KEY_LEFT:
            if self.cursor_offset >= 0:
                self.cursor_offset -= 1
            else:
                curses.beep()
        elif c == curses.KEY_RIGHT:
            if self.cursor_offset < len(self.input_buffer):
                self.cursor_offset += 1
            else:
                curses.beep()
        elif c == curses.KEY_BACKSPACE:
            self.input_buffer = self.input_buffer[:self.cursor_offset - 1] + self.input_buffer[self.cursor_offset:]
            self.cursor_offset -= 1
        elif c == curses.KEY_UP:
            self.display_pad.scroll_up(1)
        elif c == curses.KEY_DOWN:
            self.display_pad.scroll_down(1)
        elif c == curses.KEY_ENTER or c == 10 or c == 13:
            command = self.input_buffer
            self.input_buffer = ''
            self.cursor_offset = 0
            self.display_pad.reset_scroll()
            should_continue = self.handle_command(command)
        else:
            return False

        self.repaint_input_win()
        return should_continue

    def handle_command(self, command):
        cmd = command.lower()
        if cmd == 'exit':
            return False
        elif len(cmd.strip()) == 0:
            self.display_pad.write_line(' ')
        else:
            self.display_pad.write_line('Cannot parse command: {}'.format(command))
        return True

    def repaint_input_win(self):
        w = self.input_win
        buf = self.input_buffer
        cursor_pos = self.cursor_offset
        w.clear()
        w.border(' ', ' ', curses.ACS_HLINE, ' ')
        w.addstr(1, 4, '>', curses.A_BOLD)
        w.addstr(1, 6, buf[:cursor_pos])
        w.addstr(1, 6 + cursor_pos, '_', curses.A_BLINK)
        w.addstr(1, 6 + cursor_pos + 1, buf[cursor_pos:])
        w.refresh()


class ViewPane(object):
    def __init__(self):
        self.pad = None
        self.bounds = (None, None, None, None)
        self.scroll = 0
        self.max_scroll = 0
        self.current_line = 0

    def init_pad(self, x0, y0, width, height):
        self.pad = curses.newpad(10000, width)
        self.bounds = (y0, x0, y0 + height, x0 + width)
        self.current_line = height - 1

    def repaint(self):
        self.pad.refresh(self.scroll, 0, *self.bounds)

    def write_line(self, line):
        lines = textwrap.wrap(line, width=curses.COLS)
        if len(lines) != 1:
            # If the line got wrapped, or was blank, append an extra newline
            lines += ['']
        for line in lines:
            self.pad.addstr(self.current_line, 1, line)
            self.max_scroll += 1
            self.current_line += 1
            self.scroll += 1
        self.repaint()

    def scroll_down(self, num_lines):
        self.scroll = min(self.max_scroll, self.scroll + num_lines)
        self.repaint()

    def scroll_up(self, num_lines):
        self.scroll = max(0, self.scroll - num_lines)
        self.repaint()

    def reset_scroll(self):
        self.scroll = self.max_scroll
        self.repaint()


if __name__ == '__main__':
    ui = Ui()
    curses.wrapper(ui.run)
