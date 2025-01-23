"""Pages that are python objects, like functions, variables, classes etc."""
from termwiki.page import PythonFilePage
from test.data.mock_pages_root.python_objects import python_objects

python_objects_page = PythonFilePage(python_objects)


class TestVariables:
    def test_rogue_node(self):
        """
        A floating string inside a function without variable assignment.
        Should not be ignored."""
        no_return_no_assignment_page = python_objects_page.search("no_return_no_assignment")
        assert no_return_no_assignment_page
        no_return_no_assignment_page_text = no_return_no_assignment_page.read()
        assert no_return_no_assignment_page_text.splitlines()[-1] == "a rogue string"
