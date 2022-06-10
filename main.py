import asyncio
import curses
import os
import random
import re
import time
from itertools import cycle


SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
ESCAPE_KEY_CODE = 27

TIC_TIMEOUT = 0.1

BORDER_THICKNESS = 1


def load_asset_frames(dir, asset_name):
    '''Load frames of animatable ASCII asset.'''

    keyframes = dict()
    for filename in os.listdir(dir):
        if not (match := re.match(r'^rocket_frame_(\d+).txt$', filename)):
            return
        with open(os.path.join(dir, filename), 'r') as frame_file:
            keyframes[int(match.group(1))] = frame_file.read()
    return [keyframes[key] for key in sorted(keyframes)]


def draw_frame(canvas, start_row, start_column, text, negative=False):
    '''Draw multiline text fragment on canvas, erase text instead of drawing if negative=True is specified.'''
    
    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break
                
            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right corner of the window
            # Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def get_frame_size(text):
    '''Calculate size of multiline text fragment, return pair — number of rows and colums.'''
    
    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


def read_controls(canvas):
    '''Read keys pressed and returns tuple witl controls state.'''
    
    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -1

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = 1

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = 1

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -1

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

        if pressed_key_code == ESCAPE_KEY_CODE:
            # Break out of infitie loop and abort execution
            exit()
    
    return rows_direction, columns_direction, space_pressed


async def animate_ship(canvas, ship_frames, start_row=None, start_column=None, speed=1):
    '''Display controlable player ship, terminal movement speed can be changed.'''
    rows_number, columns_number = canvas.getmaxyx()
    max_row, max_col = rows_number - 1, columns_number - 1

    ship_height, ship_width = get_frame_size(ship_frames[0])

    row = (
        max(BORDER_THICKNESS, min(max_row-ship_height, start_row)) if start_row 
        else (rows_number-ship_height)//2
    )
    col = (
        max(BORDER_THICKNESS, min(max_col-ship_width, start_column)) if start_column
        else (columns_number-ship_width)//2
    )

    for frame in cycle(ship_frames):
        for _ in range(2):
            rows_direction, columns_direction, space_pressed = read_controls(canvas)

            row=max(BORDER_THICKNESS, min(max_row-ship_height, row+rows_direction*speed))
            col=max(BORDER_THICKNESS, min(max_col-ship_width, col+columns_direction*speed))

            draw_frame(canvas, row, col, frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, col, frame, negative=True)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    '''Display animation of gun shot, direction and speed can be specified.'''

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows_number, columns_number = canvas.getmaxyx()
    max_row, max_column = rows_number - 1, columns_number - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol='*'):
    '''Display animation of blinking star, star representation can be changed.'''

    canvas.addstr(row, column, symbol, curses.A_DIM)
    for _ in range(random.randint(1, 10)):
        await asyncio.sleep(0)

    while True:
        
        for _ in range(8):
            canvas.addstr(row, column, symbol, curses.A_DIM)
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        await asyncio.sleep(0)

        for _ in range(6):
            canvas.addstr(row, column, symbol, curses.A_BOLD)
            await asyncio.sleep(0)

        for _ in range(4):
            canvas.addstr(row, column, symbol)
            await asyncio.sleep(0)


def draw(canvas):
    curses.curs_set(False)

    num_starts = 100
    rows_number, columns_number = canvas.getmaxyx()
    max_row, max_col = rows_number - 1, columns_number - 1    

    canvas.border()
    canvas.nodelay(True)

    ship_frames = load_asset_frames('animations', 'rocket')

    coroutines = [
        blink(
            canvas, 
            row=random.randint(BORDER_THICKNESS, max_row-BORDER_THICKNESS), 
            column=random.randint(BORDER_THICKNESS, max_col-BORDER_THICKNESS),
            symbol=random.choice('.:*+\'')
            ) 
        for _ in range(num_starts)
    ]
    coroutines.append(
        animate_ship(canvas, ship_frames, speed=2)
    )

    # Main event loop
    
    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)

        canvas.refresh()

        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
