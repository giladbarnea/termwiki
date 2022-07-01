from termwiki import page_tree
from termwiki.render.syntax import syntax_highlight
from termwiki.util import decolor


class TestMarkdown:
    def test_plantuml(self):
        plantuml_paths, plantuml = page_tree.deep_search('plantuml')
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
