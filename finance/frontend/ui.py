import curses
import time


def main(stdscr):
    display_win, input_win = init_ui(stdscr)
    time.sleep(5)


def init_ui(stdscr):
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

    display_win = curses.newwin(display_height, max_width, title_height, 0)

    input_win = curses.newwin(input_height, max_width, title_height + display_height, 0)
    input_win.border(' ', ' ', curses.ACS_HLINE, ' ')
    input_win.addstr(1, 4, '>', curses.A_BOLD)
    input_win.addstr(1, 6, '_', curses.A_BLINK)
    input_win.refresh()

    curses.curs_set(0)

    return display_win, input_win


if __name__ == '__main__':
    curses.wrapper(main)
