from __future__ import annotations

from textwrap import indent, dedent

from termwiki.common.types import Style, Language
from termwiki.consts import IMPORT_RE, SYNTAX_HIGHLIGHT_START_RE, SYNTAX_HIGHLIGHT_END_RE, COLOR_RE, WHITESPACE_RE
from termwiki.directives import syntax
from termwiki.directives.syntax import syntax_highlight


def _get_indent_level(text: str) -> int:
    def _get_single_line_indent_level(_line: str) -> int:
        _decolored = _decolor(_line)
        _whitespace_re_match = WHITESPACE_RE.match(_decolored)
        _whitespace_re_match_span = _whitespace_re_match.span()
        return _whitespace_re_match_span[1]
    indent_level: int = min(map(_get_single_line_indent_level, text.splitlines()))
    return indent_level


def resolve_directives(text: str, default_styles: dict = None, default_style: Style = None, *args) -> str:
    # try:
    #     page_content = page(subject)
    # except TypeError as te:
    #     if te.args and re.search(r'takes \d+ positional arguments but \d+ was given', te.args[0]):
    #         page_content = page()
    #         # import logging
    #         # logging.warning('syntax() | ignored TypeError not enough pos arguments given')
    #     else:
    #         raise
    default_styles = default_styles or {}
    lines = text.splitlines()
    highlighted_strs = []
    idx = 0
    while True:
        if idx >= len(lines):
            break
        line = lines[idx]
        line_stripped = line.strip()

        if import_match := IMPORT_RE.fullmatch(line_stripped):
            # ** `%import ...`:
            from importlib import import_module
            groupdict = import_match.groupdict()
            import_path = groupdict['import_path']
            import_path, _, imported_page_name = import_path.rpartition('.')
            full_import_path = 'termwiki.pages.' + import_path.removeprefix('termwiki.pages.')
            possible_import_paths = (
                (full_import_path, None),  # absolute: import termwiki.pages.python.datamodel
                (f'.{imported_page_name}', full_import_path),  # relative: from termwiki.pages.python import datamodel
                )
            for import_name, import_package in possible_import_paths:
                imported = import_module(import_name, import_package)
                if hasattr(imported, imported_page_name):
                    imported_page = getattr(imported, imported_page_name)
                    break
            else:
                print(f"[WARNING] {groupdict['import_path']} not found")
                continue

            if hasattr(imported_page, '__handled_directives__'):
                imported_text = imported_page()
            else:
                directives_handling_imported_page = syntax(imported_page)
                imported_text = directives_handling_imported_page()
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
                highlighting_idx = idx + 1
                for _ in range(highlighted_lines_count):
                    next_line = lines[highlighting_idx]
                    highlighted = syntax_highlight(next_line, lang, style)
                    highlighted_strs.append(highlighted)
                    highlighting_idx += 1
                idx = highlighting_idx + 1
                continue  # outer while

            # * `%mysql [friendly] [--line-numbers]`:
            # idx is where %python directive.
            # Keep incrementing highlighting_idx until we hit closing /%python.
            # Then highlight idx+1:highlighting_idx.
            highlighting_idx = idx + 1
            while True:
                try:
                    next_line = lines[highlighting_idx]
                except IndexError:
                    # This happens when we keep incrementing highlighting_idx but no SYNTAX_HIGHLIGHT_END_RE is found.
                    # So we just highlight the first line and break.
                    # TODO: in setuppy, under setup(), first line not closing %bash doesnt work
                    #  Consider highlighting until end of string (better behavior and maybe solves this bug?)
                    text = lines[idx + 1]
                    highlighted = syntax_highlight(text, lang, style)
                    if enumerate_lines:
                        breakpoint()
                    highlighted_strs.append(highlighted)
                    idx = highlighting_idx
                    break  # inner while
                else:
                    if SYNTAX_HIGHLIGHT_END_RE.fullmatch(next_line.strip()):
                        text = '\n'.join(lines[idx + 1:highlighting_idx])
                        if enumerate_lines:
                            # pygments adds color codes to start of line, even if
                            # it's indented. Tighten this up before adding line numbers.
                            indent_level = _get_indent_level(text)
                            dedented_text = dedent(text)
                            ljust = len(str(highlighting_idx - (idx + 1)))
                            highlighted = syntax_highlight(dedented_text, lang, style)
                            highlighted = _enumerate_lines(highlighted, ljust=ljust)
                            highlighted = indent(highlighted, ' ' * indent_level)
                        else:
                            highlighted = syntax_highlight(text, lang, style)
                        highlighted_strs.append(highlighted)
                        idx = highlighting_idx
                        break
                    highlighting_idx += 1


        elif line_stripped.startswith('❯'):
            if '\x1b[' in line:  # hack to detect if line is already highlighted
                highlighted_strs.append(line)
            else:
                *prompt_symbol, line = line.partition('❯')
                highlighted = syntax_highlight(line, "bash", style=default_styles.get("bash", default_style))
                highlighted_strs.append(''.join(prompt_symbol) + highlighted)
        else:  # regular line, no directives (SYNTAX_HIGHLIGHT_START_RE or IMPORT_RE)
            highlighted_strs.append(line + '\n')

        idx += 1
    stripped = ''.join(highlighted_strs).strip()
    if stripped in text \
            and not '\x1b[' in text \
            and highlighted_strs[0].startswith('# '):
        # Text never included colors nor directives, and it looks like markdown
        return syntax_highlight(stripped, "markdown", style=default_styles.get("markdown", default_style))
    return stripped


def _enumerate_lines(text: str, *, ljust: int = 0) -> str:
    enumerated_text: str = '\n'.join([f'\x1b[90m{i: >{ljust}}｜\x1b[0m {line}'
                                      for i, line
                                      in enumerate(text.splitlines(), start=1)])
    return enumerated_text


def _decolor(text):
    return COLOR_RE.sub('', text)