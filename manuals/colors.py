from more_termcolor import colors

def box(text, *, width=None):
    if width is None:
        width = len(text) + 2
    horizontal_bar = '─' * width
    return '┌' + horizontal_bar + '┐\n│ ' + text + ' │\n└' + horizontal_bar + '┘'

def h1(text, **kwargs):
    return box(colors.bold(text, 'ul', 'reverse', 'bright white', **kwargs), width=len(text) + 2)


def h2(text, **kwargs):
    return colors.bold(text, 'ul', 'reverse', 'bright white', **kwargs)


def h3(text, **kwargs):
    return colors.bold(text, 'bright white', **kwargs)


def h4(text, **kwargs):  # 97 or bright white
    # return colors.brightwhite(text, 'ul', **kwargs)
    return colors.bold(text, **kwargs)


def h5(text, **kwargs):
    return colors.white(text, **kwargs)


def c(text, **kwargs):
    return colors.dark(text, **kwargs)


def i(text, **kwargs):
    return colors.italic(text, **kwargs)


def b(text, **kwargs):
    return colors.bold(text, **kwargs)


def bg(text):
    return f'\x1b[38;2;201;209;217;48;2;39;40;34m{text}\x1b[0m'


def black(text, **kwargs):
    return colors.black(text, **kwargs)

