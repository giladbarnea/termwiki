#!/usr/bin/env python3.8
from __future__ import annotations

import inspect
import itertools as it
import logging
import sys
from collections import defaultdict
from typing import Callable, Collection

import click

from termwiki.colors import h2
from termwiki.common.click_extension import unrequired_opt
from termwiki.common.types import Page
from termwiki.consts import SUB_PAGE_RE


def get_unused_sub_pages(undecorated_page_fn: Callable) -> list[str]:
    """python -m termwiki --doctor calls this"""
    # TODO (bug): Doesn't check if __LOGGING_FORMATTER in _LOGGING
    # TODO (bug): If _MANAGE = _MANAGEPY = f"""... and _MANAGEPY in last block, says _MANAGE is unused
    lines = inspect.getsource(undecorated_page_fn).splitlines()
    try:
        last_block_linenum = -next(i for i, line in enumerate(reversed(lines)) if line.strip() == 'else:') - 1
    except StopIteration:
        # no else: clause, just `return """...`
        last_block_linenum = -next(i for i, line in enumerate(reversed(lines)) if line.strip().startswith('return')) - 1
    lines_before_last_block = {line.strip().partition('=')[0].strip() for line in lines[:last_block_linenum] if
                               line and SUB_PAGE_RE.search(line) and '__' not in line}
    line_inside_last_block = {line.strip()[1:-1] for line in lines[last_block_linenum:] if
                              (stripped := line.strip()).startswith('{_') and stripped.endswith('}')}
    if lines_missing_inside_last_block := lines_before_last_block - line_inside_last_block:
        return sorted(list(lines_missing_inside_last_block))


def draw_out_decorated_fn(page: Page) -> Callable:
    # todo: use inspect.unwrap(), or page.__wrapped__
    closure: tuple = page.__closure__
    if not closure:
        # non-decorated functions' closure is None
        return page
    return closure[-1].cell_contents


def populate_pages() -> dict[str, Page]:
    """Populates a { 'pandas' : pandas , 'inspect' : inspect_, 'gh' : githubcli } dict from `termwiki` module"""
    from termwiki.pages import pages
    try:
        from .private_pages import pages as private_pages
    except ModuleNotFoundError:
        private_pages = None

    def iter_module_pages(module):
        if not module:
            return
        for _page_name in dir(module):
            if _page_name in module.EXCLUDE:
                continue
            _page: Page = getattr(module, _page_name)
            if not inspect.isfunction(_page):
                continue
            if _page_name.endswith('_'):  # inspect_()
                _name = _page_name[:-1]
            else:
                _name = _page_name
            yield _name, _page

    main_pages = dict()
    for name, page in it.chain(iter_module_pages(pages),
                               iter_module_pages(private_pages)):
        ## dont draw_out_wrapped_fn because then syntax() isn't called
        main_pages[name] = page
        if alias := getattr(page, 'alias', None):
            main_pages[alias] = page

    return main_pages


PAGES: dict[str, Page] = populate_pages()


def get_sub_page_var_names(page: Page) -> list[str]:
    return [n for n in page.__code__.co_varnames if n.isupper()]


def populate_sub_pages(*, print_unused_sub_pages=False) -> dict[str, set[Page]]:
    """Sets bash.sub_pages = [ "cut" , "for" ] for each PAGES.
    Removes (d)underscore and lowers _CUT and __FOR.
    Returns e.g. `{ 'cut' : bash , 'args' : [ bash , pdb ] }`"""
    all_sub_pages: dict[str, set[Page]] = defaultdict(set)
    for name, page in PAGES.items():

        # sub_page_var_names = [n for n in draw_out_decorated_fn(main_page_fn).__code__.co_varnames if n.isupper()]
        # draw_out_decorated_fn is necessary because PAGES has to store the fns in the wrapped form (to call them later)
        setattr(page, 'sub_pages', set())
        undecorated_main_page_fn = draw_out_decorated_fn(page)
        sub_page_var_names = get_sub_page_var_names(undecorated_main_page_fn)
        if not sub_page_var_names:
            continue

        if print_unused_sub_pages:
            unused_sub_pages = get_unused_sub_pages(undecorated_main_page_fn)
            if unused_sub_pages:
                spaces = ' ' * (max(map(len, PAGES.keys())) - len(name))
                print(f"{name!r} doesn't print:{spaces}{', '.join(unused_sub_pages)}")

        for sub_page_var_name in sub_page_var_names:
            ## DONT account for dunder __ARGUMENTS, it's being handled by get_sub_page_content().
            #   If handled here, eventually bash('_ARGUMENTS') is called which errors.
            #   likewise: if f'_{sub_page}' in page.sub_pages:

            sub_page_var_name = sub_page_var_name.strip().lower()[1:]
            page.sub_pages.add(sub_page_var_name)
            all_sub_pages[sub_page_var_name].add(page)

    return all_sub_pages


SUB_PAGES: dict[str, set[Page]] = populate_sub_pages()


def fuzzy_find_page(page: str,
                    collection: Collection,
                    *extra_opts,
                    raise_if_exhausted=False,
                    **extra_kw_opts) -> tuple:
    """If user continue'd through the whole collection, raises KeyError if `raise_if_exhausted` is True. Otherwise, returns None"""
    # not even a sub_page, could be gibberish
    # try assuming it's a substring
    from termwiki import search, prompt
    for maybes, is_last in search.iter_maybes(page, collection, criterion='substring'):
        if not maybes:
            continue

        kwargs = dict(Ep='Edit pages.py with pycharm',
                      Ec='Edit pages.py with vscode',
                      Em='Edit pages.py with micro')

        if is_last and raise_if_exhausted:
            kwargs.update(flowopts='quit')
        else:
            kwargs.update(flowopts='quit', no='continue')
        # TODO: if a match is a sub_page, present main_page.sub_page in choose
        key, choice = prompt.choose(f"Did you mean any of these?",
                                    *extra_opts,
                                    *maybes,
                                    **kwargs,
                                    **extra_kw_opts)
        if choice == prompt.Flow.CONTINUE:
            continue
        if isinstance(key, str) and key.startswith('E'):
            import os
            if key == 'Ep':
                status = os.system(f'pycharm "{__file__}"')
            elif key == 'Ec':
                status = os.system(f'code "{__file__}"')
            elif key == 'Em':
                status = os.system(f'micro "{__file__}"')
            sys.exit(status)
        return key, choice.value
    if raise_if_exhausted:
        raise KeyError(f"{page = !r} isn't in collection")
    return None, None


def get_sub_page_content(main_page: str, sub_page: str) -> str:
    """
    Function is called if both main_page and sub_page are specified.
    MAIN EXISTS?
     |      \
    yes     no
     |       \
     |      [find main]
     |        |     \
     |      found   nope
     |       /        \
     |     /        KeyError
     |   /
    SUB IN MAIN's SUBS?
     |          \
    yes         no
     |           \
    [return]    [find sub in main's]
                   |         \
                found       nope
                  |           \
                [return]    SUB IN ANY OTHER MAIN's SUBS?
                              |         \
                            yes         no
                             |           \
                            [return]    [find sub]
                                          |       \
                                        found      nope
                                          |         \
                                        [return]   KeyError
    """
    logging.debug(f"get_sub_page_content({main_page = !r}, {sub_page = !r})")
    if main_page not in PAGES:
        print(f"[info] Unknown main page: {main_page!r}. Fuzzy finding among PAGES...")
        main_page = fuzzy_find_page(main_page, PAGES, raise_if_exhausted=True)

    page: Page = PAGES[main_page]
    for sub_page_variation in (sub_page,
                               f'{sub_page}s',
                               f'_{sub_page}',
                               f'_{sub_page}s'):
        ## This accounts for 2 cases:
        # 1. 'tw python descriptor', but correct is 'descriptors', so add 's'
        # 2. 'tw bash while' -> page.sub_pages has '_while' -> pass '__WHILE'
        if sub_page_variation in page.sub_pages:
            return page(f'_{sub_page_variation.upper()}')

    try:
        # sometimes functions have alias logic under 'if subject:' clause, for example bash
        # has 'subject.startswith('<')'. so maybe sub_page works
        return page(sub_page)
    except KeyError:
        print(f"[info] sub page {sub_page!r} isn't a sub page of {main_page!r}. "
              f"Searching among {main_page!r}'s sub pages...")
        key, chosen_sub_page = fuzzy_find_page(sub_page,
                                               page.sub_pages,
                                               raise_if_exhausted=False,
                                               # keep uppercase P so doesn't collide with pages
                                               P=f"print {main_page!r} w/o sub_page")
        if key == 'P':
            return page()

        if chosen_sub_page is not None:
            return page(f'_{chosen_sub_page.upper()}')

        if sub_page in SUB_PAGES:
            print(f"[info] {sub_page!r} isn't a sub page of {main_page!r}, but it belongs to these pages:")
            return print_page(sub_page)

        print(f"[info] {sub_page!r} doesn't belong to any page. Searching among all SUB_PAGES...")
        key, sub_page = fuzzy_find_page(sub_page,
                                        SUB_PAGES,
                                        raise_if_exhausted=True,
                                        P=f"print {main_page!r} without sub_page")
        if key == 'P':
            return page()

        return page(f'_{sub_page.upper()}')


def print_page(main_page: str, sub_page=None):
    """If passed correct main_page(s), prints.
    If not correct, finds the correct with fuzzy search and calls itself."""
    logging.debug(f"print_page({main_page!r}, {sub_page!r})")
    if sub_page:
        # ** Passed both main_page and sub_page
        sub_page_str = get_sub_page_content(main_page, sub_page)
        # sub_page_str = get_sub_page_content(main_page, sub_page) \
        #     .replace('[h1]', '[bold underline reverse bright_white]') \
        #     .replace('[h2]', '[bold underline bright_white]') \
        #     .replace('[h3]', '[bold bright_white]') \
        #     .replace('[h4]', '[info]') \
        #     .replace('[h5]', '[white]') \
        #     .replace('[c]', '[dim]')
        # return console.print(sub_page_str)
        return print(sub_page_str)

    # ** Passed only one arg; could be main or sub. Maybe main?
    if main_page in PAGES:
        return print(PAGES[main_page]())

    # ** Not a main page. Maybe it's a precise sub page, i.e. "diff"
    sub_page_name = None
    if main_page in SUB_PAGES:
        sub_page_name = main_page
    else:
        for sub_page in SUB_PAGES:
            sub_page_no_leading_underscore = sub_page.removeprefix('_')
            if main_page == sub_page_no_leading_underscore:
                sub_page_name = sub_page
                break
    if sub_page_name:
        # * Indeed a precise sub_page
        ## Maybe multiple pages have it
        if len(SUB_PAGES[sub_page_name]) > 1:
            from termwiki import prompt
            pages: list[Page] = list(SUB_PAGES[sub_page_name])  # for index

            # TODO (bugs):
            #  (1) If an ALIAS of a sub_page is the same as a SUBPAGE of another main main_page,
            #    this is called (shouldn't). Aliases aren't sub_pages. (uncomment asyncio # _SUBPROCESS = _SUBPROCESSES)
            #  (2) main pages with both @alias and @syntax decors, that have the issue above ("(1)"), raise
            #    a ValueError in igit prompt, because the same main main_page function is passed here for each sub_page and sub_page alias.
            #  ValueError: ('NumOptions | __init__(opts) duplicate opts: ', ('<function asyncio at 0x7f5dab684ca0>', '<function asyncio at 0x7f5dab684ca0>', '<function python at 0x7f5dab669a60>'))
            idx, choice = prompt.choose(f"{sub_page_name!r} exists in several pages, which one did you mean?",
                                        *[page.__qualname__ for page in pages],
                                        flowopts='quit'
                                        )
            return print(pages[idx](f'_{sub_page_name.upper()}'))

        ## Unique sub_page
        page, *_ = SUB_PAGES[sub_page_name]
        return print(page(f'_{sub_page_name.upper()}'))

    # ** Not a precise sub_page. find something precise, either a main or sub main_page
    key, main_page = fuzzy_find_page(main_page,
                                     set(PAGES.keys()) | set(SUB_PAGES.keys()),
                                     raise_if_exhausted=True)
    return print_page(main_page)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('main_page', required=False)
@click.argument('sub_page', required=False)
@unrequired_opt('-l', '--list', 'list_pages_or_sub_pages', is_flag=True, help="List main page's sub pages if MAIN_PAGE is provided, else list all main pages")
@unrequired_opt('--doctor', 'print_unused_sub_pages', is_flag=True, help="Print any sub_pages that are skipped erroneously in a main page's else clause")
def get_page(main_page: str | None,
             sub_page: str | None,
             list_pages_or_sub_pages: bool = False,
             print_unused_sub_pages: bool = False):
    logging.debug(f'termwiki.get_page({main_page = !r}, {sub_page = !r}, {list_pages_or_sub_pages = }, {print_unused_sub_pages = })')
    if print_unused_sub_pages:  # tw --doctor
        populate_sub_pages(print_unused_sub_pages=True)
        return
    if list_pages_or_sub_pages:  # tw [MAIN_PAGE] -l, --list
        if main_page:
            print(f"{h2(main_page)}")
            [print(f' · {sub}') for sub in sorted(PAGES[main_page].sub_pages)]
        else:
            page: Page
            for page_name, page in sorted(PAGES.items()):
                alias = getattr(page, 'alias', None)
                if alias and alias == page_name:
                    continue
                title = f"\n{h2(page_name)}"
                if alias:
                    title += f" ({page.alias})"
                print(title)
                [print(f' · {sub}') for sub in sorted(PAGES[page_name].sub_pages)]
        return
    if not main_page:
        print('Error: Must specify a page.\n')
        ctx = get_page.context_class(get_page)
        print(get_page.get_help(ctx))
        return

    # tw MAIN_PAGE [SUB_PAGE]
    print_page(main_page, sub_page)
