from termwiki.decorators.syntax import syntax_highlight
from termwiki import page_tree


class TestMarkdown:
    def test_plantuml(self):
        plantuml = page_tree['plantuml']
        plantuml_text = plantuml.read()
        highlighted_text = syntax_highlight(plantuml_text, 'markdown')
        assert highlighted_text.startswith('┌─────────')