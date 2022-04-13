from __future__ import annotations

import ast
import inspect
import re
from functools import wraps
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
    MySqlLexer,
    PythonLexer,
    RstLexer,
    SassLexer,
    TOMLLexer,
    TypeScriptLexer,
    )

from manuals.common.types import ManFn, Style, Language
from manuals.consts import HIGHLIGHT_START_RE, LANGS, HIGHLIGHT_END_RE

# https://help.farbox.com/pygments.html     ← previews of all styles

formatters: dict[Style, TerminalTrueColorFormatter] = dict.fromkeys(Style.__args__)
lexers: dict[Language, Lexer] = dict.fromkeys(LANGS)
console = None


# *** Helper Functions

def __get_lexer_ctor(lang: Language) -> Type[Lexer]:
    if lang == 'ahk':
        return AutohotkeyLexer
    if lang == 'bash':
        return BashLexer
    if lang == 'css':
        return CssLexer
    if lang == 'docker':
        return DockerLexer
    if lang == 'ini':
        return IniLexer
    if lang == 'ipython':
        from manuals.ipython_lexer import IPython3Lexer
        return IPython3Lexer
    if lang == 'js':
        return JavascriptLexer
    if lang == 'json':
        return JsonLexer
    if lang == 'mysql':
        return MySqlLexer
    if lang == 'python':
        return PythonLexer
    if lang == 'rst':
        return RstLexer
    if lang == 'sass':
        return SassLexer
    if lang == 'toml':
        return TOMLLexer
    if lang == 'ts':
        return TypeScriptLexer
    raise ValueError(f"__get_lexer_ctor({lang = !r})")


def _get_lexer(lang: Language):
    global lexers
    lexer = lexers.get(lang)
    if lexer is None:
        ctor = __get_lexer_ctor(lang)
        lexer = ctor()
        lexers[lang] = lexer
    return lexers[lang]


def __get_color_formatter(style: Style = None):
    # default
    # friendly (less bright than native. ipython default)
    # native (like defualt with dark bg)
    # algol_nu (b&w)
    # solarized-dark (weird for python)
    # inkpot
    # monokai (good for ts)
    # fruity
    if style is None:
        style = 'monokai'
    global formatters
    formatter = formatters.get(style)
    if formatter is None:
        formatter = TerminalTrueColorFormatter(style=style)
        formatters[style] = formatter
        return formatter
    return formatter


def _highlight(text: str, lang: Language, style: Style = None) -> str:
    # print(f'{lang = !r} | {style = !r}')
    lexer = _get_lexer(lang)
    if style is None:
        if lang == 'js':
            style = 'default'
        elif lang in ('ts', 'bash', 'ipython', 'json'):
            style = 'monokai'
    formatter = __get_color_formatter(style)
    highlighted = pygments_highlight(text, lexer, formatter)
    return highlighted


# *** Decorators

def alias(_alias: str):
    """Sets `fn.alias = _alias` to decorated function.
    Used when populating MAIN_TOPICS as an additional key to function."""

    def wrap(fn: ManFn):
        fn.alias = _alias
        return fn

    return wrap


def syntax(_fn_or_style: ManFn | Style = None, **default_styles):
    """Possible forms:
    ::
        @syntax
        def foo(): ...

        @syntax('friendly')
        def foo(): ...

        @syntax(python='friendly', bash='inkpot')
        def foo(): ...

    Inline `%python native` takes precedence over decorator args.
    """
    default_style = None

    def wrap(fn: ManFn):
        @wraps(fn)  # necessary for str() to display wrapped fn and not syntax()
        def morewrap(subject=None):

            try:
                ret = fn(subject)
            except TypeError as te:
                if te.args and re.search(r'takes \d+ positional arguments but \d+ was given', te.args[0]):
                    ret = fn()
                    import logging
                    logging.warning('syntax() | ignored TypeError not enough pos arguments given')
                else:
                    raise

            lines = ret.splitlines()
            highlighted_strs = []
            idx = 0

            while True:
                try:
                    line = lines[idx]
                except IndexError as e:
                    break
                if match := HIGHLIGHT_START_RE.fullmatch(line.strip()):
                    # TODO: support %python friendly 2
                    lang, second_arg = match.groups()

                    j = idx + 1
                    if isinstance(second_arg, str) and second_arg.isdigit():
                        # e.g.: `%mysql 1`
                        if lang in default_styles:
                            # precedence to `@syntax(python='friendly')` over `@syntax('friendly')`
                            style = default_styles.get(lang)
                        else:
                            style = default_style  # may be None
                        lines_to_highlight = int(second_arg)
                        for k in range(lines_to_highlight):
                            text = lines[idx + 1]
                            highlighted = _highlight(text, lang, style)
                            highlighted_strs.append(highlighted)
                            idx += 1
                        else:
                            idx += 1
                            continue  # big while

                    # e.g.: either `%mysql` (second_arg is None) or `%mysql friendly`
                    if second_arg:
                        # give precedence to `%mysql friendly` over `**default_styles` or `@syntax('friendly')`
                        style = second_arg
                    else:
                        if lang in default_styles:
                            # precedence to `@syntax(python='friendly')` over `@syntax('friendly')`
                            style = default_styles.get(lang)
                        else:
                            style = default_style  # may be None

                    while True:
                        try:
                            nextline = lines[j]
                        except IndexError as e:
                            # no closing tag → _highlight only first line
                            # TODO: in setuppy, under setup(), first line not closing %bash doesnt work
                            #  Consider highlighting until end of string (better behavior and maybe solves this bug?)
                            text = lines[idx + 1]
                            highlighted = _highlight(text, lang, style)
                            highlighted_strs.append(highlighted)
                            idx = j
                            break
                        else:
                            if HIGHLIGHT_END_RE.fullmatch(nextline.strip()):
                                text = '\n'.join(lines[idx + 1:j])

                                highlighted = _highlight(text, lang, style)
                                highlighted_strs.append(highlighted)
                                idx = j
                                break
                            j += 1
                else:
                    highlighted_strs.append(line + '\n')
                idx += 1
            stripped = ''.join(highlighted_strs).strip()
            return stripped

        return morewrap

    if _fn_or_style is not None:
        if callable(_fn_or_style):
            # e.g. naked `@syntax`
            return wrap(_fn_or_style)
        # e.g. `@syntax(python='friendly')`
        default_style = _fn_or_style
        return wrap

    # e.g. `@syntax(python='friendly')` → **default_styles has value
    return wrap


def rich(manual: ManFn):
    @wraps(manual)
    def wrap(subject=None):
        string = manual(subject)
        from rich.markdown import Markdown
        global console
        if console is None:
            from rich.console import Console
            import io
            console = Console(file=io.StringIO(), force_terminal=True)
        # Todo - Problem: inline code is detected by indentation by builtin commonmark
        #  should build custom parser?
        md = Markdown(string, justify="left")
        console.print(md)
        marked_down = console.file.getvalue()
        return marked_down

    return wrap


def optional_subject(manual: ManFn):
    @wraps(manual)
    def decorate(subject=None):
        if not subject:
            return manual()
        fnsrc = inspect.getsource(manual)
        parsed: ast.Module = ast.parse(fnsrc)
        # noinspection PyTypeChecker
        fndef: ast.FunctionDef = parsed.body[0]
        nod: ast.Assign
        varnames: list[ast.Name]
        for nod in fndef.body:
            if not isinstance(nod, ast.Assign):
                continue
            # noinspection PyTypeChecker
            varnames = nod.targets
            for varname in varnames:
                if varname.id == subject:
                    return eval(ast.unparse(nod.value))

        return manual()

    return decorate
