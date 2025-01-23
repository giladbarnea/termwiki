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
        text = Path(
            "test/data/mock_pages_root/indentation_markdown/click.option.no-code-blocks.indented-md"
        ).read_text()
        text_lines = text.splitlines()
        indentation_markdown = IndentationMarkdown(text)
        indentation_markdown.parse()
        # import debug
        # for token in indentation_markdown:
        #     pp(token,
        #        include_file_name=False,
        #        include_function_name=False,
        #        include_arg_name=False,
        #        include_type=True)
        for i, line in enumerate(indentation_markdown.iter_text()):
            assert text_lines[i] == line.rstrip(), f"{i}: {text_lines[i]!r} != {line.rstrip()!r}"
