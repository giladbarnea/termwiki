from __future__ import annotations
from collections.abc import Sequence

from termwiki import private_pages
from termwiki.page import DirectoryPage, Page, deep_search

private_pages_tree = DirectoryPage(private_pages)


def get(page_path: Sequence[str] | str) -> tuple[list[str], Page]:
    if isinstance(page_path, str):
        page_path = page_path.split(' ')
    return deep_search(private_pages_tree, page_path)

    # if not pages:
    #     return [], private_pages_tree
    #
    # for page_name, page in private_pages_tree.traverse():
    #     current_level_pages[page_name].append(page)
    #
    # if name in current_level_pages:
    #     return current_level_pages[name]
    #
    # while True:
    #     previous_level_pages = current_level_pages.copy()
    #     current_level_pages.clear()
    #     for pages_name, pages in previous_level_pages.items():
    #         for page in pages:
    #             for sub_page_name, sub_page in page.traverse():
    #                 current_level_pages[sub_page_name].append(sub_page)
    #
    #     if name in current_level_pages:
    #         return current_level_pages[name]

    # for page_name, page in zip_pages(public_pages_tree.traverse(),
    #                                  private_pages_tree.traverse(),
    #                                  ):
    #     # public_name, public_page = public
    #     # private_name, private_page = private
    #     # current_pages[public_name] = public_page
    #     # current_pages[private_name] = private_page
    #     # current_pages[page_name] = page
    #     if page_name == name:
    #         return page
    #     current_pages.append((page_name, page))

    # while page_tuple := current_pages.popleft():
    #     page_name, page = page_tuple
    #     if page_name == name:
    #         return page
    #     # for page_name, page in self.zip_pages(current_pages.values()):
    #     #     if page_name == name:
    #     #         return page
    #     # current_pages = {page_name: page for page_name, page in self.zip_pages(current_pages.values())}
    raise AttributeError(name)
