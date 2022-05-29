from termwiki.consts import COLOR_RE
from termwiki.page import FunctionPage, PythonFilePage


def test_adhd():
    from termwiki import page_tree
    pages_page: PythonFilePage = page_tree['pages']
    adhd_page: FunctionPage = pages_page['adhd']
    adhd_text = adhd_page.read()
    adhd_text_lines = adhd_text.splitlines()
    if adhd_text_lines[0].startswith('┌'):
        title_index = 1
    else:
        title_index = 0
    decolored_title = COLOR_RE.sub('', adhd_text_lines[title_index])
    assert ''.join(filter(str.isalpha, decolored_title)).lower() == 'adhd'
