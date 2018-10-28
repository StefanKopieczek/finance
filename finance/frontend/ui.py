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
        self.display_bounds = (None, None, None, None)
        self.display_scroll = 0
        self.display_current_line = 0

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

        self.display_pad = curses.newpad(10000, max_width)
        self.display_bounds = (title_height, 0, display_height + title_height, max_width)
        self.display_current_line = display_height - 1

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
        elif c == curses.KEY_ENTER or c == 10 or c == 13:
            command = self.input_buffer
            self.input_buffer = ''
            self.cursor_offset = 0
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
            self.write_line(' ')
        else:
            self.write_line('Cannot parse command: {}'.format(command))
        return True

    def write_line(self, line):
        lines = textwrap.wrap(line, width=curses.COLS)
        if len(lines) != 1:
            # If the line got wrapped, or was blank, append an extra newline
            lines += ['']
        for line in lines:
            self.display_pad.addstr(self.display_current_line, 1, line)
            self.display_scroll += 1
            self.display_current_line += 1
        self.repaint_display_pad()

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

    def repaint_display_pad(self):
        top, left, bottom, right = self.display_bounds
        scroll = self.display_scroll
        self.display_pad.refresh(scroll, 0, top, left, bottom, right)


if __name__ == '__main__':
    ui = Ui()
    curses.wrapper(ui.run)
