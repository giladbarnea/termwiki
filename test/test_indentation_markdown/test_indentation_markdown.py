from pathlib import Path
from termwiki.indentation_markdown import IndentationMarkdown

class TestIndentationMarkdown:
    """
    1. Indentation <=> Hierarchy (no # header needed)
    2. // comments
    3. No code blocks (preserves indentation)
    4. Inline syntax highlighting with prompt: >>>
    5. Double indent ==> double header increase

    How?
    Separate to blocks
    code highlight ``` is a block regardless of indentation
    """

    def test_click_option_indented_md_no_code_blocks(self):
        # todo: check out private_pagse karabiner for example
        text = Path('test/data/mock_pages_root/indentation_markdown/click.option.no-code-blocks.indented-md').read_text()
        indentation_markdown = IndentationMarkdown(text)
        indentation_markdown.parse()
        # print()
        # print(indentation_markdown)
