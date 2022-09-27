import os
from functools import wraps, partial
from typing import Type

from pygments import highlight as pygments_highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexer import Lexer
from pygments.lexers import (
    AutohotkeyLexer,
    BashLexer,
    CssLexer,
    DockerLexer,
    GroffLexer,
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

from termwiki.common.types import PageFunction, Style, Language
from termwiki.consts import LANGS
from termwiki.ipython_lexer import IPython3Lexer

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
def _get_lexer(lang: Language) -> Lexer:
    lexer = lexers.get(lang)
    if lexer is None:
        lexer_class = lexer_classes[lang]
        lexer = lexer_class()
        lexers[lang] = lexer
    return lexers[lang]


def _get_color_formatter(style: Style) -> TerminalTrueColorFormatter:
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


def syntax_highlight(text: str, lang: Language, style: Style = None) -> str:
    global console
    if lang in ('md', 'markdown'):
        from rich.markdown import Markdown
        if console is None:
            from rich.console import Console
            console = Console(width=int(os.getenv('COLUNMS', 160)) // 2)
        with console.capture() as capture:
            console.print(Markdown(text, justify="left"))
        return capture.get()
    lexer = _get_lexer(lang)
    if not style:
        if lang == 'js':
            style = 'default'
        else:
            style = 'monokai'
    color_formatter = _get_color_formatter(style)
    highlighted = pygments_highlight(text, lexer, color_formatter)
    return highlighted


def syntax(_page_or_style: PageFunction | Style = None, **default_styles):
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

    def decorator(page: PageFunction):
        from termwiki.render import render_page
        page.__handled_directives__ = True

        return wraps(page)(partial(render_page, page, default_styles))

    if _page_or_style is not None:
        if callable(_page_or_style):
            # e.g. naked `@syntax`
            return decorator(_page_or_style)
        # e.g. `@syntax(python='friendly')`
        default_style = _page_or_style
        return decorator

    # e.g. `@syntax(python='friendly')`, so `**default_styles` has value
    return decorator
