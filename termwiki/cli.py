from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from typing import Iterable

import click
from termwiki import page_tree
from termwiki.log import log
from termwiki.render import render_page


def fuzzy_search(iterable: Iterable[str], search_term: str) -> str | None:
    command = 'echo "' + '\n'.join(iterable) + f'" | fzf --reverse -q {search_term}'
    try:
        output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as e:
        return None
    return output.decode('utf-8').strip()


def get_page(page_path: Sequence[str]) -> bool:
    # todo: on_not_found=fuzzy_search is problematic, because what if
    #  want page from another indentation?
    found_path, page = page_tree.deep_search(page_path,
                                             on_not_found=fuzzy_search,
                                             deep_search_sub_pages=True)

    if not page:
        log.warning(f'Page not found! {page_path=} | {found_path=}')
        return False

    rendered_text = render_page(page)
    print(rendered_text)
    return True


def show_help():
    log.error('Must specify a page path.\n')
    ctx = main.context_class(main)
    print(main.get_help(ctx))


@click.command(no_args_is_help=True,
               context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('page_path', required=False, nargs=-1)
def main(page_path: tuple[str]):
    if not page_path or not any(page_path):
        show_help()
        sys.exit(1)
    ok = get_page(page_path)
    sys.exit(0 if ok else 1)
