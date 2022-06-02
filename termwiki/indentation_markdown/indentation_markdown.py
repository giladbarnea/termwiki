from __future__ import annotations

from collections import deque

from termwiki.render.util import get_indent_level


def first_truthy_line_index(lines: list) -> int:
    for i, line in enumerate(lines):
        if line.strip():
            return i
    raise IndexError('All lines are empty')


class Block:
    def __init__(self, indent_level: int, parent: Block = None, lines: list[str] = None):
        self.indent_level = indent_level
        self.children: deque[Block] = deque()
        self.parent: Block = parent
        self.lines = lines or []

    def __repr__(self):
        representation = f'Block(indent_level={self.indent_level}, lines={self.lines}'
        if self.children:
            representation += f', children={", ".join(map(repr, self.children))}'
        representation += ')'
        return representation


class IndentationMarkdown:
    """Parses text into an indentation-based tree of recursive Block objects"""

    def __init__(self, text: str):
        self.text = text
        self.blocks: deque[Block] = deque()

    def parse(self):
        lines = self.text.splitlines()
        lines_count = len(lines)
        i = first_truthy_line_index(lines)
        first_line = lines[i].rstrip()
        indent_level = get_indent_level(first_line)
        current_block = Block(indent_level, lines=[first_line])
        self.blocks.append(current_block)
        i += 1
        while i < lines_count:
            line = lines[i].rstrip()
            if not line:
                current_block.lines.append(' ' * current_block.indent_level + line)
                i += 1
                continue
            indent_level = get_indent_level(line)
            if indent_level > current_block.indent_level:
                block = Block(indent_level=indent_level, parent=current_block, lines=[line])
                current_block.children.append(block)
                current_block = block
            elif indent_level == current_block.indent_level:
                current_block.lines.append(line)
            else:
                while indent_level < current_block.indent_level:
                    current_block = current_block.parent
                    current_block is None and breakpoint()
                current_block.lines.append(line)
            i += 1

    def __repr__(self):
        representation = f'IndentationMarkdown(\n'
        for block in self.blocks:
            representation += ' ' * block.indent_level + f'{block}\n'
        representation += ')'
        return representation
