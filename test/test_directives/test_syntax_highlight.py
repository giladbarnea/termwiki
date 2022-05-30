from pathlib import Path

from termwiki import page_tree
from termwiki.directives.syntax import syntax_highlight
from test.util import decolor


class TestMarkdown:
    def test_plantuml(self):
        plantuml_paths, plantuml = page_tree.get('plantuml')
        plantuml_text = plantuml.read()
        plantuml_lines = plantuml_text.splitlines()
        highlighted_text = syntax_highlight(plantuml_text, 'markdown')
        highlighted_lines = highlighted_text.splitlines()
        if '┌' in plantuml_lines[0]:
            title_index = 1
        else:
            title_index = 0
        title = plantuml_lines[title_index]
        assert decolor(highlighted_lines[0]).startswith('┌')
        assert title == '```plantuml'


class TestIndentationMarkdown:
    """
    1. Indentation <=> Hierarchy (no # header needed)
    2. // comments
    3. No code blocks (preserves indentation)
    4. Inline syntax highlighting with prompt: >>>
    5. Double indent ==> double header increase

    How?
    Separate to blocks
    code highlight ``` is a block
    """

    def test_click_option_indented_md(self):
        text = Path('test/test_directives/data/click.option.indented-md').read_text()
