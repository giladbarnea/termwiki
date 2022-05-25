# Pre-research
- [ ] https://github.com/chubin/cheat.sh

# Small

- [ ] if subtopic is not found:
  - [ ] suggest subtopics that include the searched subtopic in their text. `git fetch` doesn't exist but `git remote` includes `fetch` twice
  - [ ] search with fzf
- [ ] support for nested subtopics (e.g. `docker images ps`)
- [ ] add command: `mm edit git [EDITOR]`
- Refactoring:
  - [ ] migrate all pages in main.py to separate files
  - [ ] `populator.py`
    - [ ] find a better name about playing with functions
    - [ ] move from main.py functions like `get_skipped_subtopics` to it
- [ ] [perf] Populate (sub)topic lazily, only on demand

# Big

- [ ] `rich` markup (e.g. `[i]...[/]`)
  - [ ] see `rich/examples/log.py`
- [ ] migrate to `prompt-toolkit`? or `rich/Textual`?

# Bugs
- [ ] `mm bash --list` prints `_args` and `_arguments` as separate. should display `_args, _arguments`
- [ ] `mm regex --list` errors because regex is a subtopic, should warn and print subtopic instead
- [ ] `mm cmdl` shows one "Did you mean any of these? [0] cmd", and only after selection shows "Exists in several topics". Should sublist topics in first screen "cmd:\n[0]python cmd" etc
- [ ] `mm --doctor` says `pytest` doesn't print `_CONFTEST` even though it's a substring of `pytest.config`

---

# Separate page files a.k.a Infinite topic tree
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
- a `python` **submodule** is a topic, and it contains functions which are subtopics etc
- aliases for everything, even subtopics. like rst directives?
- (sub)topics can reference other (sub)topics (simple `import` maybe? or directive?)
- "See also: blabla" is clickable (`Textual`)
- in README.md: "optimized for zero mental overhead, specifically when getting to the info"
- mouseclick or kb shortcut to collapse / expand subtopics when shown
- `mm python magic-` for collapsed from specific hierarchy
- `mm python slots` should work even though `slots` is a python.datamodel.special_method_names() variable
- Automatic h1-h6 headings based on indentation
### %import use cases
- %import python.datamodel with python/datamodel.py and datamodel() method in datamodel.py
- %import python.datamodel.numeric with python/datamodel.py and numeric() method in datamodel.py
- %import python.datamodel.mro with python/datamodel.py and datamodel() method has _MRO variable
- %import python.datamodel with python/datamodel/{mro,descriptors}.py etc
- %import python.datamodel.mro with python/datamodel/mro text file
