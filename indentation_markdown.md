# IndentationMarkdown

- https://github.com/lark-parser/lark
- https://lucumr.pocoo.org/2015/11/18/pythons-hidden-re-gems/
- https://github.com/pyparsing/pyparsing (simple)
- https://github.com/ethanfurman/attowiki (small wiki engine for personal use.)
- [MyST](https://myst-parser.readthedocs.io/en/latest/) - Markdown for the scientific world replaces reStructuredText
- Markdown parsers:
    - [commonmark](https://github.com/readthedocs/commonmark.py)
    - [markdown-it](https://markdown-it-py.readthedocs.io/en/latest/using.html#the-parser)
        - https://github.com/executablebooks/mdit-py-plugins/blob/master/mdit_py_plugins/colon_fence.py
        - https://markdown-it-py.readthedocs.io/en/latest/using.html#the-parser

## Figure out:

- [ ] Heading like "cmdline options" should be searchable by `tw cmdline`

## Parsing

- [ ] Automatic h1-h6 headings based on indentation
- [ ] headings are pages

## Tokens

- [ ] rich markup (e.g. `[i]...[/]`)

## :import

### use cases:

- %import python.datamodel with python/datamodel.py and datamodel() method in datamodel.py
- %import python.datamodel.numeric with python/datamodel.py and numeric() method in datamodel.py
- %import python.datamodel.mro with python/datamodel.py and datamodel() method has _MRO variable
- %import python.datamodel with python/datamodel/{mro,descriptors}.py etc
- %import python.datamodel.mro with python/datamodel/mro text file