from termwiki.page import DirectoryPage
from test.data import mock_pages_root

mock_page_tree = DirectoryPage(mock_pages_root)


class TestVariables:
    def test_rogue_variable(self):
        no_return_no_assignment_page = mock_page_tree.search('no_return_no_assignment')
        assert no_return_no_assignment_page
        no_return_no_assignment_page_text = no_return_no_assignment_page.read()
        assert no_return_no_assignment_page_text.splitlines()[-1] == "a rogue string"
