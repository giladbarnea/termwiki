from termwiki.consts import COLOR_RE

def decolor(s: str) -> str:
    return COLOR_RE.sub('', s)

def cleanse_str(s: str) -> str:
    """Removes colors and all non-alphanumeric characters from a string. Strips and returns."""
    decolored_title = decolor(s)
    cleansed = ''.join(filter(str.isalpha, decolored_title)).strip()
    return cleansed