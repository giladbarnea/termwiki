# Features

## CLI

- [ ] **edit**: `tw edit git [EDITOR]`
- [ ] **-l, --list**

### Information depth control

- [ ] mouseclick or kb shortcut to collapse / expand sub_pages when shown
- [ ] `tw pecan --depth 2` to show only 2 levels of sub_pages
- [ ] `tw python magic-` for collapsed from specific hierarchy

## Inline gifs / images

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

# Similar projects

- [ ] https://github.com/chubin/cheat.sh
- [ ] geek-note
- [ ] https://github.com/xolox/vim-notes

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