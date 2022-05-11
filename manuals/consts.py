import re

from manuals.common.types import Language, Style

literal_linebreak = r'\n'
linebreak = '\n'
literal_backslash = '\\'
tab = '\t'
# color = '\x1b['
LANGS = Language.__args__
pipe_sep_langs = "|".join(LANGS)
pipe_sep_styles = "|".join(Style.__args__)


HIGHLIGHT_START_RE = re.compile( # works for 1-5
        f'%(?P<lang>{pipe_sep_langs}) ?'
        f'((?P<count>\d) *|(?P<line_numbers>--line-numbers) *|(?P<style>{pipe_sep_styles}) *)*'
        )
# print(HIGHLIGHT_START_RE.fullmatch('%python 2 --line-numbers'))  # 1
# print(HIGHLIGHT_START_RE.fullmatch('%python --line-numbers 2'))  # 2
# print(HIGHLIGHT_START_RE.fullmatch('%python --line-numbers'))    # 3
# print(HIGHLIGHT_START_RE.fullmatch('%python 2'))                 # 4
# print(HIGHLIGHT_START_RE.fullmatch('%python'))                   # 5

HIGHLIGHT_END_RE = re.compile(f'/%({pipe_sep_langs})')
SUB_TOPIC_RE = re.compile(r'_[A-Z\d_]*\s*=\s*(rf|fr|f)["\']{3}')
WHITESPACE_RE = re.compile(r'\s+')
COLOR_RE = re.compile(r'(\x1b\[(?:\d;?)*m)')
# what = re.compile(r'\b'
#                   r'(?:'
#                     # either 'one', 'two' or 'three', ending with ',' or end of word
#                     r'(?:(one)|(two)|(three))(?:,|\b)'
#                   r'){3,}' # 3 or more times
#                   r'(?(1)|(?!))'
#                   r'(?(2)|(?!))'
#                   r'(?(3)|(?!))')