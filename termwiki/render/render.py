import re
from textwrap import dedent, indent

from termwiki.common.types import Language, Style
from termwiki.consts import (
    SYNTAX_HIGHLIGHT_END_RE,
    SYNTAX_HIGHLIGHT_START_RE,
    SYNTAX_HIGHLIGHT_LINE_PREFIX_DIRECTIVES,
)
from termwiki.page import Page
from termwiki.render import syntax_highlight
from termwiki.render.util import enumerate_lines, get_indent_level

"""  # %import support
        if import_match := IMPORT_RE.fullmatch(line_stripped):
            # ** `%import ...`:
            from importlib import import_module

            groupdict = import_match.groupdict()
            import_path = groupdict["import_path"]
            import_path, _, imported_page_name = import_path.rpartition(".")
            full_import_path = "termwiki.private_pages." + import_path.removeprefix(
                "termwiki.private_pages."
            )
            possible_import_paths = (
                (
                    full_import_path,
                    None,
                ),  # absolute: import termwiki.private_pages.python.datamodel
                (
                    f".{imported_page_name}",
                    full_import_path,
                ),  # relative: from termwiki.private_pages.python import datamodel
            )
            for import_name, import_package in possible_import_paths:
                imported = import_module(import_name, import_package)
                if hasattr(imported, imported_page_name):
                    imported_page = getattr(imported, imported_page_name)
                    break
            else:
                print(f"[WARNING] {groupdict['import_path']} not found")
                continue

            should_do_properly = False
            if should_do_properly:
                renderable_page = syntax()(imported_page)
                breakpoint()  # This is not working! Not gonna wrap here with DirectoryPage like in main.
                imported_text = renderable_page()
            else:
                imported_text = imported_page
            indent_level = get_indent_level(line)
            indented_imported_text = indent(imported_text + "\n", " " * indent_level)
            highlighted_strs.append(indented_imported_text)
"""
def render_page(
    page: Page, default_styles: dict[Style, Language] = None, default_style: Style = None, *args
) -> str:
    default_styles = default_styles or {}
    remaining_text = page.read()
    remaining_text or breakpoint()
    lines = remaining_text.splitlines()
    highlighted_strs = []
    idx = 0
    while True:
        if idx >= len(lines):
            break
        line: str = lines[idx]
        line_stripped: str = line.strip()
        prefix: str = line_stripped[0] if line_stripped else ""

        # 1. Handle case where current line is a BLOCK syntax highlight directive
        if syntax_highlight_start_match := SYNTAX_HIGHLIGHT_START_RE.fullmatch(line_stripped):
            groupdict: dict = syntax_highlight_start_match.groupdict()
            lang: Language = groupdict["lang"]
            specified_line_count_to_highlight: int = int(groupdict.get("count") or 0)
            should_enumerate_lines: bool = bool(groupdict["line_numbers"])
            # Style precedence:
            # 1. %mysql friendly
            # 2. @syntax(python='friendly')
            # 3. @syntax('friendly')
            # Default_style is either @syntax('friendly') or None
            style = groupdict["style"] or default_styles.get(lang, default_style)

            # 1.a. %lang COUNT (e.g. %mysql 1)
            if specified_line_count_to_highlight:
                # Looks like this breaks %mysql 3 --line-numbers
                highlighting_idx = idx + 1
                for _ in range(specified_line_count_to_highlight):
                    next_line = lines[highlighting_idx]
                    highlighted = syntax_highlight(next_line, lang, style)
                    highlighted_strs.append(highlighted)
                    highlighting_idx += 1
                idx = highlighting_idx + 1
                continue  # Outer while

            # 1.b. %lang [friendly] [--line-numbers]
            # idx is where %lang directive.
            # Keep incrementing highlighting_idx until we hit closing /%lang.
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
                    from termwiki.log import log

                    log.warning(
                        f"No closing %lang directive found for {lang} at {idx} of page {page!r}"
                    )
                    idx = _handle_no_closing_directive(
                        lines,
                        highlighted_strs,
                        idx,
                        lang,
                        should_enumerate_lines,
                        style,
                        highlighting_idx,
                    )
                    break  # Inner while
                if SYNTAX_HIGHLIGHT_END_RE.fullmatch(next_line.strip()):
                    remaining_text = "\n".join(lines[idx + 1 : highlighting_idx])
                    if should_enumerate_lines:
                        # Pygments adds color codes to start of line, even if
                        # it's indented. Tighten this up before adding line numbers.
                        indent_level = get_indent_level(remaining_text)
                        dedented_text = dedent(remaining_text)
                        ljust = len(str(highlighting_idx - (idx + 1)))
                        highlighted = syntax_highlight(dedented_text, lang, style)
                        highlighted = enumerate_lines(highlighted, ljust=ljust)
                        highlighted = indent(highlighted, " " * indent_level)
                    else:
                        highlighted = syntax_highlight(remaining_text, lang, style)
                    highlighted_strs.append(highlighted)
                    idx = highlighting_idx
                    break  # Inner while
                highlighting_idx += 1

        # 2. Handle case where current line is a LINE syntax highlight directive
        elif prefix in SYNTAX_HIGHLIGHT_LINE_PREFIX_DIRECTIVES:
            if "\x1b[" in line:  # Hack to detect if line is already highlighted
                highlighted_strs.append(line)
            else:
                *prompt_symbol, line = line.partition(prefix)
                highlighted = syntax_highlight(
                    line,
                    SYNTAX_HIGHLIGHT_LINE_PREFIX_DIRECTIVES[prefix],
                    style=default_styles.get(
                        SYNTAX_HIGHLIGHT_LINE_PREFIX_DIRECTIVES[prefix], default_style
                    ),
                )
                highlighted_strs.append("".join(prompt_symbol) + highlighted)

        # 3. Handle case where current line is a regular line (no directives)
        else:
            highlighted_strs.append(line + "\n")

        idx += 1

    stripped_highlighted_full_string = "".join(highlighted_strs).strip()
    if (
        stripped_highlighted_full_string in remaining_text
        and "\x1b[" not in remaining_text
        and re.match("#+ ", highlighted_strs[0])
    ):
        # Text never included colors nor directives, and it looks like markdown
        dedented = "\n".join(map(str.strip, stripped_highlighted_full_string.splitlines()))
        return syntax_highlight(
            dedented, "markdown", style=default_styles.get("markdown", default_style)
        )
    return stripped_highlighted_full_string


def _handle_no_closing_directive(
    lines, highlighted_strs, idx, lang, should_enumerate_lines, style, highlighting_idx
):
    text = lines[idx + 1]
    highlighted = syntax_highlight(text, lang, style)
    if should_enumerate_lines:
        breakpoint()
    highlighted_strs.append(highlighted)
    idx = highlighting_idx
    return idx
