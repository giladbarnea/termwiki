# Pre-research
- [ ] https://github.com/chubin/cheat.sh

# Small

- [ ] if subtopic is not found:
  - [ ] suggest subtopics that include the searched subtopic in their text. `git fetch` doesn't exist but `git remote` includes `fetch` twice
  - [ ] search with fzf
- [ ] support for nested subtopics (e.g. `docker images ps`)
- [ ] add command: `mm edit git [EDITOR]`
- Refactoring:
  - [ ] migrate all manuals in main.py to separate files
  - [ ] `populator.py`
    - [ ] find a better name about playing with functions
    - [ ] move from main.py functions like `get_skipped_subtopics` to it
  

# Big

- [ ] `rich` markup (e.g. `[i]...[/]`)
  - [ ] see `rich/examples/log.py`
- [ ] migrate to `prompt-toolkit`? or `rich.Prompt`?
- [ ] Topic class
  - [ ] properties
    - [ ] alias
    - [ ] sub_topics
  
# Bugs
- [ ] `mm bash --list` prints `_args` and `_arguments` as separate. should display `_args, _arguments`
- [ ] `mm regex --list` errors because regex is a subtopic, should warn and print subtopic instead
- [ ] `mm cmdl` shows one "Did you mean any of these? [0] cmd", and only after selection shows "Exists in several topics". Should sublist topics in first screen "cmd:\n[0]python cmd" etc

# Separate man files
- support a python / markdown hybrid? https://github.com/lark-parser/lark
- [Scanner class](https://lucumr.pocoo.org/2015/11/18/pythons-hidden-re-gems/)
