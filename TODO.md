# Pre-research
- [ ] https://github.com/chubin/cheat.sh

# Small

- [ ] if sub_page is not found:
  - [ ] suggest sub_pages that include the searched sub_page in their text. `git fetch` doesn't exist but `git remote` includes `fetch` twice
  - [ ] search with fzf
- [ ] support for nested sub_pages (e.g. `docker images ps`)
- [ ] add command: `tw edit git [EDITOR]`
- Refactoring:
  - [ ] migrate all pages in main.py to separate files
  - [ ] `populator.py`
    - [ ] find a better name about playing with functions
    - [ ] move from main.py functions like `get_skipped_sub_pages` to it
- [ ] [perf] Populate (sub)page lazily, only on demand

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
### Inline gifs / images
- `gif-for-cli`
  - linux / macos.
  - `pip install gif-for-cli; gif-for-cli ./foo.gif -c █`
  - looks kinda bad, takes time to cache
- kitty icat
  - `kitty icat --align=left ./foo.gif`
  - perfect
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
