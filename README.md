# termwiki (work in progress)

## What?

`termwiki` is a personal knowledge management tool for the terminal, with a focus on **zero-thought, zero-wait** when getting to the bit you're interested in.

It also:

- Does pretty syntax highlighting and formatting with `rich`
- Supports `[[including]]` bits and files within one another
- Allows for high modularity for organizing your knowledge
- Supports dynamic pages by executing Python code

_Alternative phrasing:_
Information management for the terminal, focusing on zero-wait, zero-think when you're getting to the information you need.

_This also has a ring to it:_
Access the information you need with zero wait time and no thinking.

## Why?

Tools like Notion come with a big context switch. Navigating through the pages and waiting through loading times is awkward and slow.

When I don't remember how bash arrays work, I want to be able to type `bash array` and get whatever I wrote there, without having to leave the terminal.

I also want to edit my notes as easily as editing a local file with my editor of choice.

## Usage

    tw PATH [TO NESTED PAGE...]

`termwiki` parses the given page, then prints it.

By default, pages are looked for in `~/termwiki`, or in `TERMWIKI_PATH` if set (multiple colon-separated paths are supported).

### Basic example

Let's say you have a:

    📂 ~/termwiki/
    ├── bash.md

Typing `tw bash` pretty-prints the contents of `bash.md`:

```markdown
# Array
numbers=(1 2 3)
```

### Everything is a Page

For high modularity, `tw` treats each of these as a page:

- Plain files (`.md` or otherwise)
- Whole directories
- Python files
- Variables, functions and classes within Python files
- ...as well as within other variables / functions / classes

### Nesting pages

Pages can be arbirarily nested in other pages, with no depth limit.

Together with the `[[including]]` syntax, and the ability to run Python code, this allows for a very flexible way to organize your knowledge.

Take this example:

<pre>
📂 ~/termwiki/
├── 📂 bash/
│   ├── <b>array.md</b>       <span style="color: rgb(100,100,100)"># numbers=(1 2 3)</span>
│   ├── <b>variable.md</b>    <span style="color: rgb(100,100,100)"># hello="world"</span>
</pre>

- `tw bash` prints the contents of both `array.md` and `variable.md`, one after the other.
- `tw bash array` prints `numbers=(1 2 3)`.
- `tw bash variable` prints `hello="world"`.

### Quick access, modularity, and `[[include]]`

You can control what `tw` renders when specifying a page, by nesting same-named pages under it. So with a directory, we would add a file inside that shares the directory's name.

`termwiki` will render only this nested page, instead of rendering all the others one by one.

In our case, we would add a `bash.md` file alongside `array.md` and `variable.md`:

<pre>
📂 ~/termwiki/
├── 📂 bash/
│   ├── array.md       <span style="color: grey"># numbers=(1 2 3)</span>
│   ├── variable.md    <span style="color: grey"># hello="world"</span>
│   ├── <b>bash.md</b>
</pre>

Typing just `tw bash` now renders only `bash/bash.md`, not the other files.

If the content of `bash.md` was:

```markdown
# Array
[[bash.array]]

# For
[[bash.for]]
```

`tw bash` would print the contents of both `array.md` and `variable.md`, plus a couple of titles.

**This holds true for any type of page, including Python objects.**

Replace `bash/bash.md` with a <code>bash/<span style="font-weight: bold">bash.py</span></code>:

```python
array    = '[[bash.array]]'
variable = 'hello="world"'

def bash():
    guide = "www.etalabs.net/sh_tricks.html"
    
    return f"""# Bash
    {guide}
    {array}
    {variable}
    """
```

`tw bash` renders the return value of the `bash()` function, even though the full nesting is `directory > file > function`.

**Two things to note here:**

1. How `[[bash.array]]` can be used across different page types
2. The `guide` variable inside the `bash()` function can be accessed via `tw bash guide`.

Click here for more information about page hierarchy.

## Search, fuzzy paths, and interactive menus

If you give `tw` a path that doesn't exist, it tries hard to get what you wanted anyway, and if it's too ambiguous, it will prompt you to choose among its best guesses.

This is done in several ways:

1. When it's not really ambiguous:
    - In our example above, `tw array` would render the `array` page, even though we omitted `bash`, since it's the only `array` page in the whole tree.
    - Even if an additional `array` page existed somewhere else, but the whole `bash/` directory would be nested under a new `languages/` directory, `tw bash array` would similarily render the correct `array` page, because there's only
      one `bash > array` page.
2. File extensions are ignored, as well as letter casing, including non-alphanumeric characters (`_`, `-`, whitespace etc.) in page names.
3. Fuzzy matching (Levenstein distance), so `bash aray` works.
4. If all fails, a "Did you mean: [1] ..., [2] ..." prompt is shown.

## UX Principles

Sorted by importance:

- Instant retrieval of knowledge; must be about as quick as recalling a memory
- Easy organization of potentially complex, nested information
- Flexibility and modularity of information bits
- No editing learning curve; Just edit local files like you've been doing for years

## Extended Markdown

- `[[path.to.page]]` to include other pages, reglardless of page type
- Inline images and gifs
- Embedding links
- Proper syntax highlighting for <code>```lang</code> blocks
- Headlines are pages
- Comments
- Custom `rich` formatting

## Alternatives

`termwiki` might not be for you, in which case I would recommend either _Notion_ or _Dendron_.

Notion is the fanciest out there, and it's really good for heavy-duty, "this is my life's work" kind of usage. It's web-based, rather slow, and has an editing learning curve.

Dendron is local-first and lets you edit the files with your favorite editor, but it isn't a terminal tool (a VSCodium window), and doesn't support dynamic code execution; only static markdown files.