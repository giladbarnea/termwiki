from functools import partial, wraps
from typing import Type

from pygments import highlight as pygments_highlight
from pygments.formatters import TerminalTrueColorFormatter
from pygments.lexer import Lexer
from pygments.lexers import (
    AutohotkeyLexer,
    BashLexer,
    CssLexer,
    DockerLexer,
    HtmlLexer,
    IniLexer,
    JavascriptLexer,
    JsonLexer,
    MarkdownLexer,
    MySqlLexer,
    PostgresLexer,
    PythonLexer,
    RstLexer,
    SassLexer,
    SqlLexer,
    TOMLLexer,
    TypeScriptLexer,
    YamlLexer,
)

from termwiki import consts
from termwiki.common.types import Language, PageFunction, Style
from termwiki.ipython_lexer import IPython3Lexer

# https://help.farbox.com/pygments.html     <- previews of all styles

formatters: dict[Style, TerminalTrueColorFormatter] = dict.fromkeys(consts.STYLES)
lexer_classes: dict[Language, Type[Lexer]] = {
    "ahk": AutohotkeyLexer,
    "bash": BashLexer,
    "css": CssLexer,
    "docker": DockerLexer,
    "html": HtmlLexer,
    "ini": IniLexer,
    "ipython": IPython3Lexer,
    "js": JavascriptLexer,
    "json": JsonLexer,
    "md": MarkdownLexer,
    "markdown": MarkdownLexer,
    "mysql": MySqlLexer,
    "pql": PostgresLexer,
    "python": PythonLexer,
    "rst": RstLexer,
    "sass": SassLexer,
    "sql": SqlLexer,
    "toml": TOMLLexer,
    "ts": TypeScriptLexer,
    "yaml": YamlLexer,
    "zsh": BashLexer,
}
lexers: dict[Language, Lexer] = dict.fromkeys(consts.LANGUAGES)
assert set(lexers) == set(lexer_classes), (
    "lexers and lexer_classes must have same keys. missing in either or both:"
    f" {set(lexers) ^ set(lexer_classes)}"
)


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
    if lang in ("md", "markdown"):
        return highlight_markdown(text)

    lexer: Lexer = _get_lexer(lang)
    if not style:
        if lang == "js":
            style = "default"
        else:
            style = "monokai"
    color_formatter: TerminalTrueColorFormatter = _get_color_formatter(style)
    highlighted: str = pygments_highlight(text, lexer, color_formatter)
    return highlighted

def highlight_markdown(text: str) -> str:
    import os

    # Can't get it to syntax highlight with subprocess :(
    os.system(
        f"echo '{text}' | COLORTERM=truecolor TERM=xterm-256color /opt/homebrew/bin/glow -s dark -"
    )
    return ""
    from rich.markdown import Markdown

    from termwiki.log import console

    with console.capture() as capture:
        console.print(
            Markdown(text, justify="left", code_theme="dracula", inline_code_theme="dracula")
        )
    return capture.get()

def syntax(_page_or_style: PageFunction | Style = None, /, **default_styles):
    """
    Possible forms:
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

        return wraps(page)(partial(render_page, page, default_styles))

    if _page_or_style is not None:
        if callable(_page_or_style):
            # e.g. naked `@syntax`
            return decorator(_page_or_style)
        # e.g. `@syntax('friendly')`
        default_style = _page_or_style
        return decorator

    # e.g. `@syntax(python='friendly')`, so `**default_styles` has value
    return decorator
