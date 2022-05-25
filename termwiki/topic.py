import re
from functools import cached_property
import inspect
from typing import Generator

SUB_PAGE_RE = re.compile(r'_[A-Z]*\s?=\s?(rf|fr|f)"""')

class Topic:
    def __init__(self, fn) -> None:
        self.fn = fn
    
    def __call__(self, *args, **kwargs):
        pass

    @cached_property
    def wrapped(self):
        closure: tuple = self.fn.__closure__
        if not closure:
            # non-decorated functions' closure is None
            return self.fn
        return closure[-1].cell_contents

class MainTopic(Topic):
    
    def __init__(self, fn) -> None:
        super().__init__(fn)
    
    @cached_property
    def sub_page_var_names(self) -> Generator[str]:
        for sub_page_var_name in self._extract_sub_page_var_names_from_source():
            yield sub_page_var_name
    
    def _extract_sub_page_var_names_from_source(self) -> Generator[str]:
        wrapped = self.wrapped
        for sub_page_var_name in wrapped.__code__.co_varnames:
            if not sub_page_var_name.isupper():
                continue
            sub_page_name = sub_page_var_name.strip().lower()[1:]
            yield sub_page_name
    
    def print_unused_sub_pages(self):
        """python -m termwiki <MAIN PAGE> --doctor calls this"""
        wrapped = self.wrapped
        lines = inspect.getsource(wrapped).splitlines()
        try:
            last_else_idx = -next(i for i, line in enumerate(reversed(lines)) if line.strip() == 'else:') - 1
        except StopIteration:
            # no else: clause, just return (like click)
            last_else_idx = -next(i for i, line in enumerate(reversed(lines)) if line.strip().startswith('return ')) - 1
        before_else = [line.strip().partition('=')[0].strip() for line in lines[:last_else_idx] if
                       line and SUB_PAGE_RE.search(line) and not '__' in line]
        after_else = [line.strip()[1:-1] for line in lines[last_else_idx:] if
                      (stripped := line.strip()).startswith('{_') and stripped.endswith('}')]
        if diff := set(before_else).difference(set(after_else)):
            import logging
            logging.warning(f'{wrapped.__name__}() doesnt print: {diff}')
