from termwiki.consts import COLOR_RE

def decolor(s: str) -> str:
    return COLOR_RE.sub('', s)

def clean_str(s: str) -> str:
    """Removes colors and all non-alphanumeric characters from a string,
     except leading and trailing underscores.
     Strips and returns."""
    decolored = decolor(s).strip()
    cleaned = []
    for i, char in enumerate(decolored):
        if char.isalnum():
            cleaned.append(char)
        elif i > 0 and cleaned and char == '_':
            cleaned.append(char)

    # cleansed = ''.join(filter(str.isalpha, decolored)).strip()
    # return cleansed
    return ''.join(cleaned)