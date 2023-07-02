from termwiki.page import DirectoryPage
from test.data.mock_pages_root import different_name

different_name_tree = DirectoryPage(different_name)


def test_read_all_subpages_if_no_self_named_page():
    """When a sub page exists with the same name as its parent,
    parent.read() reads only this sub page. But if a self-named sub page doesn't exist,
    parent.read() reads all sub pages."""
    no_self_named_files_directory: DirectoryPage = different_name_tree.search("no-self-named-files")
    different_name_python_file = no_self_named_files_directory.search("different_name")
    hard_to_reach_function = different_name_python_file.search("hard_to_reach")
    assert hard_to_reach_function.read() == "long way"

    toldya_markdown_file = no_self_named_files_directory.search("toldya")
    assert toldya_markdown_file.read() == "surprise"

    no_self_named_files_directory_text = no_self_named_files_directory.read()
    assert hard_to_reach_function.read() in no_self_named_files_directory_text
    assert toldya_markdown_file.read() in no_self_named_files_directory_text
