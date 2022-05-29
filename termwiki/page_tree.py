from collections import defaultdict

from termwiki import pages as public_pages, private_pages
from termwiki.page import DirectoryPage, Page

public_pages_tree = DirectoryPage(public_pages)
private_pages_tree = DirectoryPage(private_pages)


# def zip_pages(*page_iterators):
#     fillvalue = []
#     [fillvalue.append(None) for _ in page_iterators]
#     for zipped_pages in zip_longest(*page_iterators, fillvalue=fillvalue):
#         for page_tuple in zipped_pages:
#             page_name, page = page_tuple
#             yield page_name, page


def get(name) -> list[Page]:
    if not name:
        raise AttributeError(name)
    current_level_pages: defaultdict[str, list[Page]] = defaultdict(list)
    for page_name, page in public_pages_tree.traverse():
        current_level_pages[page_name].append(page)
    for page_name, page in private_pages_tree.traverse():
        current_level_pages[page_name].append(page)

    if name in current_level_pages:
        return current_level_pages[name]

    while True:
        previous_level_pages = current_level_pages.copy()
        current_level_pages.clear()
        for pages_name, pages in previous_level_pages.items():
            for page in pages:
                for sub_page_name, sub_page in page.traverse():
                    current_level_pages[sub_page_name].append(sub_page)

        if name in current_level_pages:
            return current_level_pages[name]

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
