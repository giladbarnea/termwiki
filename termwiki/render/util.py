from __future__ import annotations

from termwiki.consts import WHITESPACE_RE, COLOR_RE


def get_indent_level(text: str) -> int:
    def _get_single_line_indent_level(_line: str) -> int:
        _decolored = decolor(_line)
        _whitespace_re_match = WHITESPACE_RE.match(_decolored)
        _whitespace_re_match_span = _whitespace_re_match.span()
        return _whitespace_re_match_span[1]
    indent_level: int = min(map(_get_single_line_indent_level, text.splitlines()))
    return indent_level


def enumerate_lines(text: str, *, ljust: int = 0) -> str:
    enumerated_text: str = '\n'.join([f'\x1b[90m{i: >{ljust}}｜\x1b[0m {line}'
                                      for i, line
                                      in enumerate(text.splitlines(), start=1)])
    return enumerated_text


def decolor(text):
    return COLOR_RE.sub('', text)
