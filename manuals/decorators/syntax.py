from __future__ import annotations

import re
from functools import wraps
from textwrap import dedent, indent
from typing import Type

from pygments import highlight as pygments_highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexer import Lexer
from pygments.lexers import (
    AutohotkeyLexer,
    BashLexer,
    CssLexer,
    DockerLexer,
    IniLexer,
    JavascriptLexer,
    JsonLexer,
    MarkdownLexer,
    MySqlLexer,
    PythonLexer,
    RstLexer,
    SassLexer,
    TOMLLexer,
    TypeScriptLexer,
    )

from manuals.common.types import ManFn, Style, Language
from manuals.consts import SYNTAX_HIGHLIGHT_START_RE, LANGS, SYNTAX_HIGHLIGHT_END_RE, WHITESPACE_RE, COLOR_RE, IMPORT_RE
from manuals.ipython_lexer import IPython3Lexer

# https://help.farbox.com/pygments.html     <- previews of all styles

formatters: dict[Style, TerminalTrueColorFormatter] = dict.fromkeys(Style.__args__)
lexer_classes: dict[Language, Type[Lexer]] = {
    'ahk':      AutohotkeyLexer,
    'bash':     BashLexer,
    'css':      CssLexer,
    'docker':   DockerLexer,
    'ini':      IniLexer,
    'ipython':  IPython3Lexer,
    'js':       JavascriptLexer,
    'json':     JsonLexer,
    'md':       MarkdownLexer,
    'markdown': MarkdownLexer,
    'mysql':    MySqlLexer,
    'python':   PythonLexer,
    'rst':      RstLexer,
    'sass':     SassLexer,
    'toml':     TOMLLexer,
    'ts':       TypeScriptLexer,
    }
lexers: dict[Language, Lexer] = dict.fromkeys(LANGS)
console = None


# *** Helper Functions
def _decolor(text):
    return COLOR_RE.sub('', text)


def _get_lexer(lang: Language) -> Lexer:
    lexer = lexers.get(lang)
    if lexer is None:
        # ctor = __get_lexer_ctor(lang)
        lexer_class = lexer_classes[lang]
        lexer = lexer_class()
        lexers[lang] = lexer
    return lexers[lang]


def _get_color_formatter(style: Style):
    # default
    # friendly (less bright than native. ipython default)
    # native (like defualt with dark bg)
    # algol_nu (b&w)
    # solarized-dark (weird for python)
    # inkpot
    # monokai (good for ts)
    # fruity
    formatter = formatters.get(style)
    if formatter is None:
        formatter = TerminalTrueColorFormatter(style=style)
        formatters[style] = formatter
        return formatter
    return formatter


def _get_indent_level(text: str) -> int:
    indent_level: int = min(map(lambda line: WHITESPACE_RE.match(_decolor(line)).span()[1],
                                text.splitlines()))
    return indent_level


def _enumerate_lines(text: str, *, ljust: int = 0) -> str:
    enumerated_text: str = '\n'.join([f'\x1b[90m{i: >{ljust}}｜\x1b[0m {line}'
                                      for i, line
                                      in enumerate(text.splitlines(), start=1)])
    return enumerated_text


def _syntax_highlight(text: str, lang: Language, style: Style = None) -> str:
    lexer = _get_lexer(lang)
    if not style:
        if lang == 'js':
            style = 'default'
        else:
            style = 'monokai'
    color_formatter = _get_color_formatter(style)
    highlighted = pygments_highlight(text, lexer, color_formatter)
    return highlighted


def syntax(_manual_or_style: ManFn | Style = None, **default_styles):
    """Possible forms:
    ::
        @syntax
        def foo(): ...

        @syntax('friendly')
        def foo(): ...

        @syntax(python='friendly', bash='inkpot')
        def foo(): ...

    Inline `%python native` takes precedence over decorator args.

    **Flow:**

    Outer while:

    - line = lines[idx]; idx++. Break when idx == len(lines).
    - If line matches %import:
    - If line matches SYNTAX_HIGHLIGHT_START_RE:

      - Get `lang` from line.
      - Get `style` from line > kwargs > args.
      - if `highlighted_lines_count` is specified (--line-numbers):

        - Highlight respective lines starting from idx+1
        - Set `idx` to the line after the last highlighted line and continue outer loop.

      - if `highlighted_lines_count` is specified (--line-numbers):

    """
    default_style = None

    def decorator(manual: ManFn):
        manual.__handled_directives__ = True

        @wraps(manual)
        def manual_that_handles_directives(subject=None) -> str:

            try:
                manual_content = manual(subject)
            except TypeError as te:
                if te.args and re.search(r'takes \d+ positional arguments but \d+ was given', te.args[0]):
                    manual_content = manual()
                    # import logging
                    # logging.warning('syntax() | ignored TypeError not enough pos arguments given')
                else:
                    raise

            lines = manual_content.splitlines()
            highlighted_strs = []
            idx = 0
            while True:
                if idx == len(lines):
                    break
                line = lines[idx]
                line_stripped = line.strip()

                if import_match := IMPORT_RE.fullmatch(line_stripped):
                    # ** `%import ...`:
                    from importlib import import_module
                    groupdict = import_match.groupdict()
                    import_path = groupdict['import_path']
                    import_path, _, imported_manual_name = import_path.rpartition('.')
                    full_import_path = 'manuals.man.' + import_path.removeprefix('manuals.man.')
                    module = import_module(full_import_path)
                    imported_manual = getattr(module, imported_manual_name)
                    if hasattr(imported_manual, '__handled_directives__'):
                        imported_text = imported_manual()
                    else:
                        directives_handling_imported_manual = syntax(imported_manual)
                        imported_text = directives_handling_imported_manual()
                    indent_level = _get_indent_level(line)
                    indented_imported_text = indent(imported_text + '\n', ' ' * indent_level)
                    highlighted_strs.append(indented_imported_text)

                elif syntax_highlight_start_match := SYNTAX_HIGHLIGHT_START_RE.fullmatch(line_stripped):
                    # ** `%mysql ...`:
                    groupdict: dict = syntax_highlight_start_match.groupdict()
                    lang: Language = groupdict['lang']
                    highlighted_lines_count: int = groupdict['count'] and int(groupdict['count'])
                    enumerate_lines: bool = bool(groupdict['line_numbers'])
                    # style precedence:
                    # 1. %mysql friendly
                    # 2. @syntax(python='friendly')
                    # 3. @syntax('friendly')
                    style = groupdict['style']
                    if not style:
                        # default_style is either @syntax('friendly') or None
                        style = default_styles.get(lang, default_style)

                    # * `%mysql 1`:
                    if highlighted_lines_count:
                        # looks like this breaks %mysql 3 --line-numbers
                        highlight_start_idx = idx + 1
                        for _ in range(highlighted_lines_count):
                            next_line = lines[highlight_start_idx]
                            highlighted = _syntax_highlight(next_line, lang, style)
                            highlighted_strs.append(highlighted)
                            highlight_start_idx += 1
                        idx = highlight_start_idx + 1
                        continue  # outer while

                    # * `%mysql [friendly] [--line-numbers]`:
                    # idx is where %python directive.
                    # Keep incrementing highlight_start_idx until we hit closing /%python.
                    # Then highlight idx+1:highlight_start_idx.
                    highlight_start_idx = idx + 1
                    while True:
                        try:
                            next_line = lines[highlight_start_idx]
                        except IndexError:
                            # This happens when we keep incrementing highlight_start_idx but no SYNTAX_HIGHLIGHT_END_RE is found.
                            # So we just highlight the first line and break.
                            # TODO: in setuppy, under setup(), first line not closing %bash doesnt work
                            #  Consider highlighting until end of string (better behavior and maybe solves this bug?)
                            text = lines[idx + 1]
                            highlighted = _syntax_highlight(text, lang, style)
                            if enumerate_lines:
                                breakpoint()
                            highlighted_strs.append(highlighted)
                            idx = highlight_start_idx
                            break  # inner while
                        else:
                            if SYNTAX_HIGHLIGHT_END_RE.fullmatch(next_line.strip()):
                                text = '\n'.join(lines[idx + 1:highlight_start_idx])
                                if enumerate_lines:
                                    # pygments adds color codes to start of line, even if
                                    # it's indented. Tighten this up before adding line numbers.
                                    indent_level = _get_indent_level(text)
                                    dedented_text = dedent(text)
                                    ljust = len(str(highlight_start_idx - (idx + 1)))
                                    highlighted = _syntax_highlight(dedented_text, lang, style)
                                    highlighted = _enumerate_lines(highlighted, ljust=ljust)
                                    highlighted = indent(highlighted, ' ' * indent_level)
                                else:
                                    highlighted = _syntax_highlight(text, lang, style)
                                highlighted_strs.append(highlighted)
                                idx = highlight_start_idx
                                break
                            highlight_start_idx += 1


                elif line_stripped.startswith('❯'):
                    if '\x1b[' in line:  # hack to detect if line is already highlighted
                        highlighted_strs.append(line)
                    else:
                        *prompt_symbol, line = line.partition('❯')
                        highlighted = _syntax_highlight(line, "bash", style=default_styles.get("bash", default_style))
                        highlighted_strs.append(''.join(prompt_symbol) + highlighted)
                else:  # regular line, no directives (SYNTAX_HIGHLIGHT_START_RE or IMPORT_RE)
                    highlighted_strs.append(line + '\n')

                idx += 1
            stripped = ''.join(highlighted_strs).strip()
            return stripped

        return manual_that_handles_directives

    if _manual_or_style is not None:
        if callable(_manual_or_style):
            # e.g. naked `@syntax`
            return decorator(_manual_or_style)
        # e.g. `@syntax(python='friendly')`
        default_style = _manual_or_style
        return decorator

    # e.g. `@syntax(python='friendly')`, so `**default_styles` has value
    return decorator
