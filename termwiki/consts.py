import os
import re
from pathlib import Path

import termwiki

PROJECT_ROOT_PATH = str(Path(termwiki.__path__[0]).parent) + "/"
DEBUG: bool = os.getenv("TERMWIKI_DEBUG", "true").lower() in ("1", "true")
PYCHARM_HOSTED = os.getenv("PYCHARM_HOSTED", "0") == "1"
NON_INTERACTIVE_WIDTH = 160

literal_linebreak = r"\n"
linebreak = "\n"
literal_backslash = "\\"
tab = "\t"
# color = '\x1b['

LANGUAGES: list[str] = [
    "ahk",
    "bash",
    "css",
    "docker",
    "html",
    "ini",
    "ipython",
    "js",
    "json",
    "md",
    "markdown",
    "mysql",
    "pql",
    "python",
    "rst",
    "sass",
    "sql",
    "toml",
    "ts",
    "yaml",
    "zsh",
]

STYLES: list[str] = [
    "algol_nu",
    "default",
    "dracula",
    "friendly",
    "fruity",
    "inkpot",
    "monokai",
    "native",
    "solarized-dark",
]

PIPE_SEPARATED_LANGUAGES = "|".join(LANGUAGES)
PIPE_SEPARATED_STYLES = "|".join(STYLES)

SYNTAX_DIRECTIVE_OPEN_RE = "(%|```)"
SYNTAX_DIRECTIVE_CLOSE_RE = "(/%|```)"

# Works for cases 1-5 below
SYNTAX_HIGHLIGHT_START_RE = re.compile(
    rf"{SYNTAX_DIRECTIVE_OPEN_RE}(?P<lang>{PIPE_SEPARATED_LANGUAGES}) ?"
    r"((?P<count>\d) *|(?P<line_numbers>--line-numbers) *|(?P<style>{pipe_sep_styles}) *)*"
)
# print(SYNTAX_HIGHLIGHT_START_RE.fullmatch('%python 2 --line-numbers'))  # 1
# print(SYNTAX_HIGHLIGHT_START_RE.fullmatch('%python --line-numbers 2'))  # 2
# print(SYNTAX_HIGHLIGHT_START_RE.fullmatch('%python --line-numbers'))    # 3
# print(SYNTAX_HIGHLIGHT_START_RE.fullmatch('%python 2'))                 # 4
# print(SYNTAX_HIGHLIGHT_START_RE.fullmatch('%python'))                   # 5

SYNTAX_HIGHLIGHT_END_RE = re.compile(
    f"{SYNTAX_DIRECTIVE_CLOSE_RE}(?P<lang>{PIPE_SEPARATED_LANGUAGES})?"
)

IMPORT_RE = re.compile(r"%import (?P<import_path>[\w.]+)")

SUB_PAGE_RE = re.compile(r'_[A-Z\d_]*\s*=\s*(rf|fr|f)["\']{3}')
WHITESPACE_RE = re.compile(r"\s*")
COLOR_RE = re.compile(r"(\x1b\[(?:\d;?)*m)")
NON_LETTER_RE = re.compile(r"[^a-zA-Z\d]")
SYNTAX_HIGHLIGHT_LINE_PREFIX_DIRECTIVES = {
    "$": "bash",
    "❯": "zsh",
    ">>>": "python",
    "...": "python",
}
# what = re.compile(r'\b'
#                   r'(?:'
#                     # either 'one', 'two' or 'three', ending with ',' or end of word
#                     r'(?:(one)|(two)|(three))(?:,|\b)'
#                   r'){3,}' # 3 or more times
#                   r'(?(1)|(?!))'
#                   r'(?(2)|(?!))'
#                   r'(?(3)|(?!))')
