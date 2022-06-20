from __future__ import annotations

import re
from typing import Sized


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
