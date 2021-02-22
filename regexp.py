import re
from contextlib import suppress
from re import Pattern

from more_termcolor import colors

BACKSLASH: str = '\\'
FILE_CHAR: str = r'[\w\d-]'
PATH_WILDCARD: str = fr'[\.\*\\]'
NOT_PATH_WILDCARD: str = r'[^\.\*\\]'
FILE_SUFFIX: Pattern = re.compile(r'\.+[\w\d]{1,5}')
# TRAILING_RE: Pattern = re.compile(fr"({PATH_WILDCARD}*{FILE_CHAR}*)({PATH_WILDCARD}*)")
# LEADING_RE: Pattern = re.compile(fr'({PATH_WILDCARD}*)(.*$)')
YES_OR_NO: Pattern = re.compile(r'(yes|no|y|n)(\s.*)?', re.IGNORECASE)

ONLY_REGEX: Pattern = re.compile(r'[\^.\\+?*()|\[\]{}<>$]+')  # TODO: why escape closing curly bracket?

# e.g [a-z0-9]
SQUARE_BRACKETS_REGEX = re.compile(r'\[([a-z](-[a-z])?|[0-9](-[0-9])?)+\]', re.IGNORECASE)
ADV_REGEX_CHAR = BACKSLASH + '+()|{}$^<>'
ADV_REGEX_2CHAR = ['.*', '.+', '.?', '(?']  # TODO: "*.*" is simple glob but 'has adv regex'

GLOB_CHAR = '?*![]'  # TODO: detect "[a-z]" but dont false positive on mere "-"

REGEX_CHAR = GLOB_CHAR + ADV_REGEX_CHAR

# fullmatch('f5905f1') or fullmatch('f5905f1e4ab6bd82fb6644ca4cc2799a59ee725d')
SHA_RE = re.compile(r'([a-f\d]{7}|[a-f\d]{40})')


def is_only_regex(val: str):
    r"""
    # TODO: all but the 0th item fail the test
    >>> all([is_only_regex(val) for val in ['.*', '[a-z]', '[^\w]{1,3}$', '(?:\d)+(.*)', '[^\w]', '\w']])
    True
    """
    if not val:
        return False
    if re.fullmatch(ONLY_REGEX, val):
        return True
    return False
    # TODO: this is not really tested, for ex. it fails detecting [abc]. also, account for lookbehinds etc
    without_sqr_brackets = SQUARE_BRACKETS_REGEX.sub('', val)
    if without_sqr_brackets == val:
        return False
    if without_sqr_brackets == '' or is_only_regex(without_sqr_brackets):
        # '^[a-z]*$' → '^*$' → True
        return True
    return False


def is_glob_char(whole_string: str, char_idx: int) -> bool:
    r"""
    >>> all([is_glob_char(val, i) for val, i in [('[a-z]', 0), ('*.*py', 2), ('!d*', 0)]])
    True
    >>> any([is_glob_char(val, i) for val, i in [('[^a-z]', 0), ('*(.)*', 2), ('!\d*', 0)]])
    False
    """
    char = whole_string[char_idx]
    if char in GLOB_CHAR:
        # ('[^\w]', 0) isn't glob and should return False.
        with suppress(IndexError):
            if whole_string[char_idx - 1] in ADV_REGEX_CHAR:
                return False
        with suppress(IndexError):
            if whole_string[char_idx + 1] in ADV_REGEX_CHAR:
                return False
        return True
    return False


def has_glob(val: str) -> bool:
    r"""
    >>> all([has_glob(val) for val in ['src/**/*', '[a-z123]', '[!x-z789]']])
    True
    >>> any([has_glob(val) for val in ['src/', '[^\w]{1,3}$', '(?<=foo)bar']])
    False

    Note: this function is still susceptible to ambiguous strings, i.e. 'foo[a-z]*'
    """
    if not val:
        return False
    for i, c in enumerate(val):
        if is_glob_char(val, i):
            return True
    return False


def is_only_glob(val: str) -> bool:
    # TODO: this doesn't detect [a-z]
    if not val:
        return False
    for i in range(len(val)):
        if not is_glob_char(val, i):
            return False
    return True


def has_regex(val: str):  # doesnt detect single dot
    r"""True if any char is 'magic', from simple glob to advanced regex.
    Has to be a compilable pattern. This means that some glob patterns aren't considered regex, like 'src/**/*'.
    >>> all([has_regex(val) for val in ['src/.*', '[a-z123]', '[!x-z789]', '[^\w]{1,3}$', '(?<=foo)bar']])
    True
    >>> any([has_regex(val) for val in ['src/','src/**/*', r'(?bad)lookbehind']])
    False
    """
    if not val:
        return False
    for i, c in enumerate(val):
        if c in REGEX_CHAR:
            try:
                re.compile(val)
            except re.error:
                # 'src/**/*' has 'c in REGEX_CHAR', but isn't regex and should return False.
                # Raises on compile.
                # Note: this function is still susceptible to ambiguous strings, i.e. 'foo[a-z]*'
                return False
            else:
                return True
        try:
            if c + val[i + 1] in ADV_REGEX_2CHAR:
                return True
        except IndexError:
            pass
    return False


# TODO: consider using is_only_regex() in these two functions
def endswith_regex(val: str) -> bool:  # doesnt detect single dot
    if not val:
        return False
    end = val[-1]
    return end in REGEX_CHAR or val[-2:] in ADV_REGEX_2CHAR


def startswith_regex(val: str):
    if not val:
        return False
    start = val[0]
    return start in REGEX_CHAR or val[:2] in ADV_REGEX_2CHAR


def has_adv_regex(val: str):
    r"""
    True if any char is advanced regex. False if `val` is a simple glob.
    Has to be a compilable pattern.
    >>> all([has_adv_regex(val) for val in ['src/.*', '[^\w]{1,3}$', '(?<=foo)bar']])
    True
    >>> any([has_adv_regex(val) for val in ['[a-z123]', '[!x-z789]', 'foo*', 'src/**/*']])
    False
    """
    if not val:
        return False
    for i, c in enumerate(val):
        if c in ADV_REGEX_CHAR:
            try:
                re.compile(val)
            except re.error:
                return False
            else:
                return True
        try:
            if c + val[i + 1] in ADV_REGEX_2CHAR:
                return True
        except IndexError:
            pass
    return False


def make_word_separators_optional(val):
    return re.sub('[-_. ]', '[-_. ]', val)


def strip_trailing_path_wildcards(val):
    """Strips any [/.*\\] from the end. Doesn't strip from the beginning.
    Use with dirs.
    Doesn't handle file extensions well (i.e. 'py_venv.xml' loses suffix)"""
    
    match = re.match(rf"([*.\\/]*[^*.\\]*)([*.\\/]*)", val)
    groups = match.groups()
    if ''.join(groups) != val:
        print(colors.yellow(f"strip_trailing_path_wildcards({repr(val)}): regex stripped away too much, returning as-is. groups: {', '.join(map(repr, groups))}"))
        return val
    return groups[0]


def strip_leading_path_wildcards(val):
    """Strips any [/.*\\] from the beginning. Doesn't strip from the end.
    Use with dirs or files.
    Handles file extensions well (i.e. 'py_venv.xml' keeps suffix)"""
    match = re.match(fr'({PATH_WILDCARD}*)(.*$)', val)
    path_wildcard, rest = match.groups()
    if path_wildcard == '.':
        # not regex if dot isn't accompanied by other chars; '.git' has no regex
        return val
    return rest


def strip_surrounding_path_wildcards(val):
    """Strips any [/.*\\] from the beginning and end. Use with dirs.
    Doesn't handle file extensions well (i.e. 'py_venv.xml' loses suffix)"""
    return strip_trailing_path_wildcards(strip_leading_path_wildcards(val))
