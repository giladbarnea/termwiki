# from termwiki.log import log
from termwiki.page import DirectoryPage, MarkdownFilePage, MergedPage
from test.data import mock_pages_root

mock_page_tree = DirectoryPage(mock_pages_root)


def test_same_name_same_level_not_all_readable():
    """bash/ dir exists as well as pages.py bash() function.
    bash/ dir has only an irrelevant file, but it's detected first by DirectoryPage.
    So we expect 'search', which filters falsy Pages, to return only the FunctionPage('bash')"""
    # orig_search = mock_page_tree.__class__.search
    # mock_page_tree.__class__.search = log.log_in_out(orig_search)
    bash = mock_page_tree.search('bash')
    assert bash
    bash_text = bash.read()
    assert bash_text == "pages.py bash() function"
    # mock_page_tree.__class__.search = orig_search


def test_same_name_same_level_all_readable():
    """readable/readable.py with 'readable' var exists,
    as well as plain readable.md file."""
    merged_readable_markdown_and_directory: MergedPage = mock_page_tree.search('readable')
    assert len(merged_readable_markdown_and_directory.pages) == 2

    readable_directory = next((p for p in merged_readable_markdown_and_directory.pages if isinstance(p, DirectoryPage)))

    readable_directory_text = readable_directory.read()
    assert readable_directory_text == "readable variable in readable/readable.py readable()"
    assert readable_directory.search('readable')
    assert readable_directory.search('readable').read() == readable_directory_text

    readable_md_file = next((p for p in merged_readable_markdown_and_directory.pages if isinstance(p, MarkdownFilePage)))
    readable_md_file_text = readable_md_file.read()
    assert readable_md_file_text == "readable.md content"

    # Assert MergedPage
    assert mock_page_tree.search('readable').read()


def test_searching_with_extension_returns_only_specific_page():
    readable_markdown_file = mock_page_tree.search('readable.md')
    readable_markdown_file_text = readable_markdown_file.read()
    assert readable_markdown_file_text == "readable.md content"
