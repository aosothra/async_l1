import asyncio
import curses
import os
import random
import re
import time
from itertools import cycle

from physics import update_speed
from curses_tools import draw_frame, get_frame_size, read_controls
from obstacles import Obstacle, show_obstacles


TIC_TIMEOUT = 0.1
BORDER_THICKNESS = 1
PHRASES = {
    # Только на английском, Repl.it ломается на кириллице
    1957: "First Sputnik",
    1961: "Gagarin flew!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "Take the plasma gun! Shoot the garbage!",
}


coroutines = []
obstacles = []
collided_obstacles = []
year = 1957
is_gameover = False

def load_asset_frames(dir, asset_name):
    '''Load frames of animatable ASCII asset.'''

    keyframes = dict()
    for filename in os.listdir(dir):
        if not (match := re.match(fr'^{asset_name}_frame_(\d+).txt$', filename)):
            continue
        with open(os.path.join(dir, filename), 'r') as frame_file:
            keyframes[int(match.group(1))] = frame_file.read()
    return [keyframes[key] for key in sorted(keyframes)]


def load_asset_sprite_collection(dir):
    '''Load sprite collection from folder'''

    sprite_collection = dict()
    for filename in os.listdir(dir):
        with open(os.path.join(dir, filename), 'r') as sprite_file:
            asset_name = os.path.splitext(filename)[0]
            sprite_collection[asset_name] = sprite_file.read()
    return sprite_collection


def get_garbage_delay_tics(year):
    '''Get delay based on game progress'''

    if year < 1961:
        return None
    elif year < 1969:
        return 20
    elif year < 1981:
        return 14
    elif year < 1995:
        return 10
    elif year < 2010:
        return 8
    elif year < 2020:
        return 6
    else:
        return 2


async def slumber(seconds=1):
    '''Delay coroutine execution by specified time'''

    for _ in range(seconds):
        await asyncio.sleep(0)


async def animate_ship(canvas, main_window, ship_frames, start_row=None, start_column=None, speed=1):
    '''Display controlable player ship, terminal movement speed can be changed.'''

    global coroutines, obstacles, collided_obstacles, is_gameover

    gun_invention_year = 2020

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
    row_speed = column_speed = 0

    for frame in cycle(ship_frames):
        for _ in range(2):
            for obstacle in obstacles:
                if not obstacle.has_collision(row, col, obj_size_columns=ship_width, obj_size_rows=ship_height):
                    continue
                collided_obstacles.append(obstacle)
                is_gameover = True
                await explode(canvas, row+ship_width/2, col+ship_height/2)
                await show_gameover(canvas)
                return

            rows_direction, columns_direction, space_pressed = read_controls(main_window)

            row_speed, column_speed = update_speed(row_speed, column_speed, rows_direction, columns_direction)

            row=max(BORDER_THICKNESS, min(max_row-ship_height, row+row_speed))
            col=max(BORDER_THICKNESS, min(max_col-ship_width, col+column_speed))

            draw_frame(canvas, row, col, frame)

            if space_pressed and year>=gun_invention_year:
                coroutines.append(
                    fire(canvas, row, col+ship_width/2, rows_speed=-1)
                )
            await asyncio.sleep(0)
            draw_frame(canvas, row, col, frame, negative=True)


async def show_gameover(canvas):
    '''Displays animated GAME OVER message'''
    gameover_frames = load_asset_frames('animations', 'gameover')
    rows_number, columns_number = canvas.getmaxyx()

    while True:
        for frame in cycle(gameover_frames):
            row_size, column_size = get_frame_size(frame)
            draw_frame(canvas, rows_number/2-row_size/2+1, columns_number/2-column_size/2, frame)
            await asyncio.sleep(0)
            draw_frame(canvas, rows_number/2-row_size/2+1, columns_number/2-column_size/2, frame, negative=True)
            


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    '''Display animation of gun shot, direction and speed can be specified.'''
    global obstacles, collided_obstacles

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
        for obstacle in obstacles:
            if not obstacle.has_collision(row, column):
                continue
            collided_obstacles.append(obstacle)
            return
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, symbol='*'):
    '''Display animation of blinking star, star representation can be changed.'''

    canvas.addstr(row, column, symbol, curses.A_DIM)
    await slumber(random.randint(1, 10))

    while True:
        
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await slumber(8) 

        canvas.addstr(row, column, symbol)
        await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await slumber(6)

        for _ in range(4):
            canvas.addstr(row, column, symbol)
        await slumber(4)


async def fly_garbage(canvas, column, garbage_frame, obstacle, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    global obstacles, collided_obstacles

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)
    row_size, column_size = get_frame_size(garbage_frame)

    row = 0

    while row < rows_number:
        if obstacle in collided_obstacles:
            collided_obstacles.remove(obstacle)
            break
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
        obstacle.row = row
    
    obstacles.remove(obstacle)
    await explode(canvas, row+row_size/2, column+column_size/2)


async def fill_orbit_with_garbage(canvas, garbage_sprites):
    '''Periodicaly create garbage entities'''
    global obstacles, year
    rows_number, columns_number = canvas.getmaxyx()

    while True:
        delay = get_garbage_delay_tics(year)
        if is_gameover:
            return
        if not delay:
            await slumber()
        else:
            sprite = random.choice(list(garbage_sprites.values()))
            column = random.randint(0, columns_number)

            row_size, column_size = get_frame_size(sprite)

            obstacle = Obstacle(0, column, row_size, column_size)
            obstacles.append(obstacle)

            coroutines.append(
                fly_garbage(canvas, column, sprite, obstacle)
            )

            await slumber(delay)


async def explode(canvas, center_row, center_column):
    '''Draw explosion animation'''

    explosion_frames = load_asset_frames('animations', 'explosion')
    rows, columns = get_frame_size(explosion_frames[0])
    corner_row = center_row - rows / 2
    corner_column = center_column - columns / 2

    curses.beep()
    for frame in explosion_frames:
        draw_frame(canvas, corner_row, corner_column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, corner_row, corner_column, frame, negative=True)
        await asyncio.sleep(0)


async def update_year(canvas):
    '''Update game year clock and display trivia'''

    global year, is_gameover

    rows_number, columns_number = canvas.getmaxyx()

    while True:
        if is_gameover:
            return
        year+=1
        if phrase:=PHRASES.get(year):
            panel_text= f'{year}: {phrase}'
        else:
            panel_text= f'{year}'
        canvas.erase()
        canvas.addstr(1, int(columns_number/2-len(panel_text)/2), panel_text, curses.A_DIM)
        await slumber(30)


def draw(canvas):
    curses.curs_set(False)

    global coroutines, obstacles, collided_obstacles

    num_starts = 100
    rows_number, columns_number = canvas.getmaxyx()
    max_row, max_col = rows_number - 1, columns_number - 1
    panel_rows = 3   

    canvas.nodelay(True)
    display = canvas.derwin(rows_number-panel_rows, columns_number, 0, 0)
    display_rows, display_columns = display.getmaxyx()

    panel = canvas.derwin(panel_rows, columns_number, rows_number-panel_rows, 0)

    ship_frames = load_asset_frames('animations', 'rocket')
    garbage_sprites = load_asset_sprite_collection('sprites/garbage')

    coroutines = [
        blink(
            display, 
            row=random.randint(BORDER_THICKNESS, display_rows-BORDER_THICKNESS), 
            column=random.randint(BORDER_THICKNESS, display_columns-BORDER_THICKNESS),
            symbol=random.choice('.:*+\'')
            ) 
        for _ in range(num_starts)
    ]
    coroutines.append(
        fill_orbit_with_garbage(display, garbage_sprites)
    )
    coroutines.append(
        animate_ship(display, canvas, ship_frames, speed=2)
    )
    coroutines.append(
        update_year(panel)
    )

    # Main event loop    
    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        
        display.border()
        display.refresh()
        panel.border()
        panel.refresh()
        
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
