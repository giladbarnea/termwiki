import os
from collections.abc import Generator

from .page import Traversable, Page


class MergedPage(Traversable):
    """A page that is the merge of several pages"""

    def __init__(self, pages: dict[str, Page]) -> None:
        super().__init__()
        self.pages = pages

    def __repr__(self) -> str:
        if self.pages:
            shorten_line = lambda line: line[:30] + ' ... ' + line[-30:] if len(line) > 65 else line
            pages_values = list(self.pages.values())
            first_page_repr = repr(pages_values[0])
            first_page_short_repr = shorten_line(first_page_repr)
            if len(self.pages) == 1:
                pages_repr = f'[{first_page_short_repr}]'
            else:
                second_page_repr = repr(pages_values[1])
                second_page_short_repr = shorten_line(second_page_repr)
                if len(self.pages) == 2:
                    pages_repr = f'[\n\t\t{first_page_short_repr},\n\t\t{second_page_short_repr}]'
                else:
                    last_page_repr = repr(pages_values[-1])
                    last_page_short_repr = shorten_line(last_page_repr)
                    if len(self.pages) == 3:
                        pages_repr = f'[\n\t\t{first_page_short_repr},' \
                                     f'\n\t\t{second_page_short_repr},' \
                                     f'\n\t\t{last_page_short_repr}]'
                    else:
                        pages_repr = f'[\n\t\t{first_page_short_repr},' \
                                     f'\n\t\t{second_page_short_repr},' \
                                     f'\n\t\t... ({len(self.pages) - 3} more),' \
                                     f'\n\t\t{last_page_short_repr}]'


        else:
            pages_repr = '[]'

        if os.environ.get('PYCHARM_HOSTED'):
            pages_repr = pages_repr.replace('\n\t\t', "", 1).replace('\n\t\t', ", ")  # remove first \n\t\t
        return f'{self.__class__.__name__}(pages={pages_repr})'

    def name(self) -> str:
        safe_page_name = lambda page: page.name() if hasattr(page, 'name') else page.__class__.__name__
        prefix = self.__class__.__name__ + '('
        joiner_str = '\n\t\t' if os.environ.get('PYCHARM_HOSTED') else ', '
        sub_pages_names = joiner_str.join(safe_page_name(page) for page in self.pages.values())
        return prefix + sub_pages_names + ')'

    def merge_sub_pages(self) -> "MergedPage":
        sub_pages: dict[str, Page] = {}
        for name, page in self.pages.items():
            if isinstance(page, MergedPage):
                print('self:\n', self)
                print('page:\n', page)
                raise RuntimeError(f'MergedPage.merge_sub_pages, '
                                   f'one of the sub-pages is a MergedPage! '
                                   f'this should not happen (I think). '
                                   f'printed self and page above')
            if hasattr(page, 'pages'):
                sub_pages.update(page.pages)
            else:
                sub_pages[name] = page

        if sub_pages == self.pages:
            return self
        merged_sub_pages = MergedPage(sub_pages)
        return merged_sub_pages

    def traverse(self, *args, cache_ok=True, **kwargs) -> Generator[tuple[str, Page]]:
        for name, page in self.pages.items():
            if hasattr(page, 'traverse'):
                yield from page.traverse()

    def read(self, *args, **kwargs) -> str:
        page_texts = []
        for name, page in self.pages.items():
            if page.readable:
                page_text = page.read()
                page_texts.append(page_text)
        return '\n\n'.join(page_texts)
