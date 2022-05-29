import click
from termwiki import page_tree
from termwiki.directives import resolve_directives


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('pages', required=False, nargs=-1)
def get_page(pages: tuple[str]):
    """
    Get a page.
    """
    first_level_name, *pages = pages
    first_level_pages = page_tree.get(first_level_name)
    if len(first_level_pages) > 1:
        if not pages:
            print(f'Not Implemented yet! {first_level_name = !r}, {first_level_pages = }')
            return
        print('Should iterate over pages, see which page doesnt dead-end')
        breakpoint()
    page = first_level_pages[0]
    for page_name in pages:
        page = page[page_name]
    page_text = page.read()
    resolved_directives = resolve_directives(page_text)
    print(resolved_directives)
