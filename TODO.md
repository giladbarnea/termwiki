# Pre-research

- [ ] https://github.com/chubin/cheat.sh

# Small

- [ ] fuzziness with fzf
- [ ] add command: `tw edit git [EDITOR]`
- [x] support for nested sub_pages (e.g. `docker images ps`)
- [x] Refactoring:
    - [x] migrate all pages in main.py to separate files
    - [x] `populator.py`
        - [x] find a better name about playing with functions
        - [x] move from main.py functions like `get_skipped_sub_pages` to it
- [x] [perf] Populate (sub)page lazily, only on demand

# Big

- [ ] `rich` markup (e.g. `[i]...[/]`)
    - [ ] see `rich/examples/log.py`
- [ ] migrate to `prompt-toolkit`? or `rich/Textual`?

# Bugs

- [ ] `tw bash --list` prints `_args` and `_arguments` as separate. should display `_args, _arguments`
- [ ] `tw regex --list` errors because regex is a sub_page, should warn and print sub_page instead
- [ ] `tw cmdl` shows one "Did you mean any of these? [0] cmd", and only after selection shows "Exists in several pages". Should sublist pages in first screen "cmd:\n[0]python cmd" etc
- [ ] `tw --doctor` says `pytest` doesn't print `_CONFTEST` even though it's a substring of `pytest.config`

---

# Separate page files a.k.a Infinite page tree

## Markdown / Python hybrid

- https://github.com/lark-parser/lark
- https://lucumr.pocoo.org/2015/11/18/pythons-hidden-re-gems/
- Markdown parsers:
  - [commonmark](https://github.com/readthedocs/commonmark.py)
  - [markdown-it](https://markdown-it-py.readthedocs.io/en/latest/using.html#the-parser)
    - https://github.com/executablebooks/mdit-py-plugins/blob/master/mdit_py_plugins/colon_fence.py
    - https://markdown-it-py.readthedocs.io/en/latest/using.html#the-parser

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

## Brain dump

- a `python` **submodule** is a page, and it contains functions which are sub_pages etc
- aliases for everything, even sub_pages. like rst directives?
- (sub)pages can reference other (sub)pages (simple `import` maybe? or directive?)
- "See also: blabla" is clickable (`Textual`)
- in README.md: "optimized for zero mental overhead, specifically when getting to the info"
- mouseclick or kb shortcut to collapse / expand sub_pages when shown
- `tw python magic-` for collapsed from specific hierarchy
- `tw python slots` should work even though `slots` is a python.datamodel.special_method_names() variable
- Automatic h1-h6 headings based on indentation

### %import use cases

- %import python.datamodel with python/datamodel.py and datamodel() method in datamodel.py
- %import python.datamodel.numeric with python/datamodel.py and numeric() method in datamodel.py
- %import python.datamodel.mro with python/datamodel.py and datamodel() method has _MRO variable
- %import python.datamodel with python/datamodel/{mro,descriptors}.py etc
- %import python.datamodel.mro with python/datamodel/mro text file
