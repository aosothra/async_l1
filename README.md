# async_l1 - Eldritch horrors of Terminal Space... 2

This project implements rudimentary async event loop in a manner of a small game.

### Installation guidelines


You must have Python3 installed on your system.

This project relies on [curses](https://docs.python.org/3/library/curses.html) library, that is native to Python, but is not supported by Windows. 

You may use `pip` (or `pip3` to avoid conflict with Python2) to install a [Windows port](https://pypi.org/project/windows-curses/) of this library.
```sh
pip install -r requirements.txt
```

### Basic usage (for the lack of any other...)

```sh
py main.py
```

Use arrow keys to move your ship around. 

You can abort execution by pressing `ESC`.

### Project goals

This project was created for educational purposes as part of [dvmn.org](https://dvmn.org/) Backend Developer course.

