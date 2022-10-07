import subprocess
import sys
from collections.abc import Sequence
from typing import Iterable

import click
from termwiki import page_tree
from termwiki.page import Page, PageNotFound
from termwiki.render import render_page
from termwiki.log import log, log_in_out
@log_in_out
def fuzzy_search(iterable: Iterable[str], search_term: str) -> str | None:
    # --exit-0 --select-1 --inline-info
    command = 'echo "' + '\n'.join(iterable) + (f'" | fzf --header-first --header="{search_term} not found; did you mean..." '
                                               # f'--no-select-1 --no-exit-0 '
                                               f'--cycle --reverse -q {search_term}')
    try:
        output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as e:
        log.error(f'Fuzzy search failed with {type(e).__qualname__}: {e}')
        return None
    return output.decode('utf-8').strip()


def get_page(page_path: Sequence[str]) -> tuple[list[str], Page]:
    # todo: on_not_found=fuzzy_search is problematic, because what if
    #  want page from another indentation?
    found_path, page = page_tree.deep_search(page_path,
                                             on_not_found=fuzzy_search,
                                             recursive=True)

    if not page:
        error =f'Page not found! {page_path=} | {found_path=}'
        raise PageNotFound(error)

    return found_path, page
    rendered_text = render_page(page)
    print(rendered_text)
    return True

def print_subpages(page):
    list(page.traverse())
    print(page.name())
    [print(f' · {p}') for p in page.pages]
    return True

def show_help():
    log.error('Must specify a page path.\n')
    ctx = main.context_class(main)
    print(main.get_help(ctx))


@click.command(no_args_is_help=True,
               context_settings=dict(help_option_names=['-', '--help']))
@click.argument('page_path', required=False, nargs=-1)
@click.option('-l', '--list', 'list_subpages', is_flag=True, help='List subpages')
def main(page_path: tuple[str], list_subpages: bool):
    if not page_path or not any(page_path):
        show_help()
        return sys.exit(1)
    try:
        found_path, page = get_page(page_path)
    except Exception as e:
        log.error(repr(e),exc_info=True)
        return sys.exit(1)

    if list_subpages:
        return print_subpages(page)

    rendered_text = render_page(page)
    print(rendered_text)
    return sys.exit(0)