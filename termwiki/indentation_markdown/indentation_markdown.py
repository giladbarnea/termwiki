from __future__ import annotations
from collections import deque
from termwiki.render.util import get_indent_level
from termwiki.util import short_repr


def traverse_block(block: Block):
    for line in block.lines:
        yield line
        if isinstance(line, Header):
            yield from traverse_block(line.block)


def first_truthy_line_index(lines: list) -> int:
    for i, line in enumerate(lines):
        if line.strip():
            return i
    raise IndexError("All lines are empty")


class Line(str):
    def __new__(cls, text: str, *args, **kwargs):
        return str.__new__(cls, text)

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"


class Header(Line):
    def __new__(cls, text: str, level: int, block: Block = None):
        self = super().__new__(cls, text)
        self.level = level
        self.block = block
        return self

    def __repr__(self):
        return f"{self.__class__.__name__}({short_repr(str(self))}, level={self.level}, block={short_repr(self.block)})"


class Block:
    def __init__(
        self,
        indent_level: int,
        parent: Block = None,
        lines: list[Line] = None,
        start_index: int = None,
    ):
        self.indent_level = indent_level
        self.children: deque[Block] = deque()
        self.parent: Block = parent
        self.lines: list[Line] = lines or []
        self.start_index = start_index

    def index_of_last_truthy_line(self) -> int:
        for i in reversed(range(len(self.lines))):
            if self.lines[i].rstrip():
                return i
        raise IndexError("All lines are empty")

    def headerize_last_line(self, global_indent_size: int) -> Header:
        index_of_last_truthy_line = self.index_of_last_truthy_line()
        assert isinstance(self.lines[index_of_last_truthy_line], str), type(
            self.lines[index_of_last_truthy_line]
        )
        last_truthy_line = self.lines[index_of_last_truthy_line]
        # +1 because indent=0 -> h1
        header_level = (self.indent_level // global_indent_size) + 1
        header = Header(last_truthy_line, header_level)
        self.lines[index_of_last_truthy_line] = header
        return header

    def short_repr(self):
        return (
            f"{self.__class__.__name__}(start_index={self.start_index}, "
            f"indent_level={self.indent_level}, ...)"
        )

    def __repr__(self):
        representation = (
            f"{self.__class__.__name__}(start_index={self.start_index}, "
            f"indent_level={self.indent_level}, \n\t"
            f"lines={short_repr(self.lines)}"
        )
        if self.children:
            representation += f",\n\tchildren={short_repr(self.children)}"
        representation += ")"
        return representation


class IndentationMarkdown:
    """Parses text into an indentation-based tree of recursive Block objects.

    A headline is a line that has a lower indentation than its following line,


    """

    def __init__(self, text: str):
        self.text = text
        self.blocks: deque[Block] = deque()

    def parse(self):
        lines = self.text.splitlines()
        lines_count = len(lines)
        i = first_truthy_line_index(lines)
        first_line = lines[i].rstrip()
        indent_level = get_indent_level(first_line)
        global_indent_size = indent_level
        current_block = Block(indent_level, lines=[Line(first_line)], start_index=i)
        self.blocks.append(current_block)
        i += 1
        while i < lines_count:
            line = lines[i].rstrip()
            if not line:
                current_block.lines.append(Line(" " * current_block.indent_level))
                i += 1
                continue

            indent_level = get_indent_level(line)
            if global_indent_size == 0:
                # this doesn't account for when first line is indented a lot
                global_indent_size = indent_level
            elif indent_level % global_indent_size != 0:
                raise SyntaxError(
                    f"Inconsistent indentation: "
                    f"global indent size is {global_indent_size}, "
                    f"but line (#{i}) indent size is {indent_level}.\n"
                    f"Line: {line}"
                )
            line = Line(line)
            if indent_level > current_block.indent_level:
                empty_trailing_lines = deque()
                while not current_block.lines[-1].rstrip():
                    empty_trailing_lines.appendleft(current_block.lines.pop())
                block = Block(
                    indent_level=indent_level,
                    parent=current_block,
                    lines=[*empty_trailing_lines, line],
                    start_index=i,
                )
                header = current_block.headerize_last_line(global_indent_size)
                header.block = block
                current_block.children.append(block)
                current_block = block
            elif indent_level == current_block.indent_level:
                current_block.lines.append(line)
            else:
                while indent_level < current_block.indent_level:
                    if current_block.parent is None:
                        # probably self.blocks.append( new block )
                        breakpoint()
                    current_block = current_block.parent
                current_block.lines.append(line)
            i += 1

    def iter_tokens(self):
        for block in self.blocks:
            yield from traverse_block(block)

    __iter__ = iter_tokens

    def iter_text(self):
        for token in self:
            yield str(token)

    def __repr__(self):
        representation = f"{self.__class__.__name__}(\n"
        for block in self.blocks:
            representation += " " * block.indent_level + f"{block}\n"
        representation += ")"
        return representation
