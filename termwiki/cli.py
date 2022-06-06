from collections.abc import Sequence
import sys
import click

from termwiki import page_tree
from termwiki.render import render_page
from termwiki.log import log


def get_page(page_path: Sequence[str]) -> bool:
    found_path, page = page_tree.deep_search(page_path)
    if not page:
        log.warning(f'Page not found! {page_path=} | {found_path=}')
        return False
    rendered_text = render_page(page)
    print(rendered_text)
    return True
    # first_level_name, *pages = pages
    # first_level_pages = page_tree.get(first_level_name)
    # if len(first_level_pages) > 1:
    #     if not pages:
    #         print(f'Not Implemented yet! {first_level_name = !r}, {first_level_pages = }')
    #         return
    #     print('Should iterate over pages, see which page doesnt dead-end')
    #     breakpoint()
    # page = first_level_pages[0]
    # for page_name in pages:
    #     page = page[page_name]
    # page_text = page.read()
    # resolved_directives = render_page(page_text)
    # print(resolved_directives)

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


