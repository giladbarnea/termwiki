from __future__ import annotations

import re
from typing import Sized

from termwiki.consts import COLOR_RE


def short_repr(obj: Sized) -> str:
    if type(obj) is str:
        obj: str
        lines = obj.splitlines()
        if len(lines) > 2:
            return repr('\n'.join([lines[0], '…', lines[-1]]))
        if len(obj) > 75:
            return obj[:40] + '…' + obj[-40:]
        return obj

    if hasattr(obj, 'short_repr'):
        return obj.short_repr()

    if len(obj) > 2:
        empty_sequence_repr = repr(type(obj)())
        match = re.match(r'\w+', empty_sequence_repr)
        if match:
            type_name = match.group()
            parens = empty_sequence_repr[match.end():]
            left_parens, right_parens = parens[:len(parens)], parens[len(parens):]
        else:
            type_name = ''
            left_parens, right_parens = empty_sequence_repr
        return f'{type_name}{left_parens}{obj[0]!r}, ..., {obj[-1]!r}{right_parens}'
    return repr(obj)


def decolor(text):
    return COLOR_RE.sub('', text)


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
