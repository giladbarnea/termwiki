# Features

## CLI

- [ ] **edit**: `tw edit git [EDITOR]`
- [ ] **-l, --list**

### Information depth control

- [ ] mouseclick or kb shortcut to collapse / expand sub_pages when shown
- [ ] `tw pecan --depth 2` to show only 2 levels of sub_pages
- [ ] `tw python magic-` for collapsed from specific hierarchy

## General Brain dump

- [ ] (sub)pages can reference other (sub)pages (simple `import` maybe? or directive?)
- [ ] "See also: blabla" is clickable (`Textual`)
- [ ] in README.md: "optimized for zero mental overhead, specifically when getting to the info"

## `Page`

- Can this be ast parsed? when `tw ws`

```python
def ws():
    # https://example.com
```

- [ ] **aliases** for everything, even sub_pages. like rst directives?

---

## IndentationMarkdown

- https://github.com/lark-parser/lark
- https://lucumr.pocoo.org/2015/11/18/pythons-hidden-re-gems/
- Markdown parsers:
    - [commonmark](https://github.com/readthedocs/commonmark.py)
    - [markdown-it](https://markdown-it-py.readthedocs.io/en/latest/using.html#the-parser)
        - https://github.com/executablebooks/mdit-py-plugins/blob/master/mdit_py_plugins/colon_fence.py
        - https://markdown-it-py.readthedocs.io/en/latest/using.html#the-parser

### Parsing

- [ ] Automatic h1-h6 headings based on indentation (?)

### Tokens

- [ ] rich markup (e.g. `[i]...[/]`)

### :import

#### use cases:

- %import python.datamodel with python/datamodel.py and datamodel() method in datamodel.py
- %import python.datamodel.numeric with python/datamodel.py and numeric() method in datamodel.py
- %import python.datamodel.mro with python/datamodel.py and datamodel() method has _MRO variable
- %import python.datamodel with python/datamodel/{mro,descriptors}.py etc
- %import python.datamodel.mro with python/datamodel/mro text file

### Inline gifs / images

- gifs:
    - `gif-for-cli`
        - linux / macos.
        - `pip install gif-for-cli; gif-for-cli ./foo.gif -c █`
        - looks kinda bad, takes time to cache
    - kitty icat
        - `kitty icat --align=left ./foo.gif`
        - perfect
- images:
    - ImageMagick?
    - image-to-ansi.py, 11 years old: https://gist.github.com/klange/1687427
    - climage (rather pixelated)
    - https://github.com/hzeller/timg supports kitty, iTerm2 and wezterm full res protocols
    - https://askubuntu.com/questions/97542/how-do-i-make-my-terminal-display-graphical-pictures
    - https://pypi.org/project/imgrender/
    - sxiv
    - https://linux.die.net/man/1/feh
    - https://github.com/seebye/ueberzug#dependencies

---

# Similar projects

- [ ] https://github.com/chubin/cheat.sh

---

# Bugs

- [ ] `tw python slots` should work even though `slots` is a python.datamodel.special_method_names() variable
- [ ] `tw sed` prints restructured_text and not `bash > sed`. Should give more weight to next-level page if exact match.

---

# Done

- [x] fuzziness with fzf
- [x] support for nested sub_pages (e.g. `docker images ps`)
- [x] a `python` **submodule** is a page, and it contains functions which are sub_pages etc
- [x] Refactoring:
    - [x] migrate all pages in main.py to separate files
    - [x] `populator.py`
        - [x] find a better name about playing with functions
        - [x] move from main.py functions like `get_skipped_sub_pages` to it
- [x] [perf] Populate (sub)page lazily, only on demand