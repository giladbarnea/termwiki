import re

from manuals.common.types import Language, Style

literal_linebreak = r'\n'
linebreak = '\n'
literal_backslash = '\\'
tab = '\t'
# color = '\x1b['
LANGS = Language.__args__
HIGHLIGHT_START_RE = re.compile(fr'%({"|".join(LANGS)}) ?(\d|{"|".join(Style.__args__)})?')
HIGHLIGHT_END_RE = re.compile(fr'/%({"|".join(LANGS)})')
SUB_TOPIC_RE = re.compile(r'_[A-Z0-9_]*\s*=\s*(rf|fr|f)["\']{3}')