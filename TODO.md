# Pre-research
- [ ] https://github.com/chubin/cheat.sh

# Small

- [ ] if subtopic is not found:
  - [ ] suggest subtopics that include the searched subtopic in their text. `git fetch` doesn't exist but `git remote` includes `fetch` twice
  - [ ] search with fzf
- [ ] migrate all manuals in main.py to separate files
- [ ] support for nested subtopics (e.g. `docker images ps`)
- [ ] add command: `mm edit git [EDITOR]`
- [ ] `populator.py`
  - [ ] find a better name about playing with functions
  - [ ] move from main.py functions like `get_skipped_subtopics` to it
  


# Big

- [ ] `rich` markup (e.g. `[i]...[/]`)
- [ ] migrate to `prompt-toolkit`?
- [ ] Topic class
  - [ ] properties
    - [ ] alias
    - [ ] sub_topics
  

# Thoughts

- [ ] separate man files: support `.md`, maybe `.rst`?