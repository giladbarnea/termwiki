from more_termcolor import colors


def h1(text, **kwargs):
    return colors.bold(text, 'ul', 'reverse', 'bright white', **kwargs)


def h2(text, **kwargs):
    return colors.bold(text, 'ul', 'bright white', **kwargs)


def h3(text, **kwargs):
    return colors.bold(text, 'bright white', **kwargs)


def h4(text, **kwargs):  # 97 or bright white
    return colors.brightwhite(text, **kwargs)


def h5(text, **kwargs):
    return colors.white(text, **kwargs)


def c(text, **kwargs):
    return colors.dark(text, **kwargs)


def i(text, **kwargs):
    return colors.italic(text, **kwargs)


def b(text, **kwargs):
    return colors.bold(text, **kwargs)

def bg(text):
    return f'\x1b[38;2;130;130;130;48;2;15;15;15m{text}\x1b[0m'
def black(text, **kwargs):
    return colors.black(text, **kwargs)





