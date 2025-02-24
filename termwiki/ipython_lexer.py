# -*- coding: utf-8 -*-
"""
Defines a variety of Pygments lexers for highlighting IPython code.

This includes:

    IPythonLexer, IPython3Lexer
        Lexers for pure IPython (python + magic/shell commands)

    IPythonPartialTracebackLexer, IPythonTracebackLexer
        Supports 2.x and 3.x via keyword `python3`.  The partial traceback
        lexer reads everything but the Python code appearing in a traceback.
        The full lexer combines the partial lexer with an IPython lexer.

    IPythonConsoleLexer
        A lexer for IPython console sessions, with support for tracebacks.

    IPyLexer
        A friendly lexer which examines the first line of text and from it,
        decides whether to use an IPython lexer or an IPython console lexer.
        This is probably the only lexer that needs to be explicitly added
        to Pygments.

"""

# -----------------------------------------------------------------------------
# Copyright (c) 2013, the IPython Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------
# https://pygments.org/docs/lexerdevelopment/
# Standard library
import re

from pygments.lexer import bygroups, using  # Lexer, DelegatingLexer, RegexLexer, do_insertions

# Third party
from pygments.lexers import (
    BashLexer,
    HtmlLexer,
    JavascriptLexer,
    PerlLexer,
    Python3Lexer,
    PythonLexer,
    RubyLexer,
    TexLexer,
)
from pygments.token import Keyword, Operator, Text  # Generic, Literal, Name, Other, Error,

# from pygments.util import get_bool_opt

# Local

line_re = re.compile(".*?\n")

__all__ = ["IPython3Lexer", "build_ipy_lexer"]


def build_ipy_lexer(python3):
    """
    Builds IPython lexers depending on the value of `python3`.

    The lexer inherits from an appropriate Python lexer and then adds
    information about IPython specific keywords (i.e. magic commands,
    shell commands, etc.)

    Parameters
    ----------
    python3 : bool
        If `True`, then build an IPython lexer from a Python 3 lexer.

    """
    PyLexer = Python3Lexer
    name = "IPython3"
    aliases = ["ipython3"]
    doc = """IPython3 Lexer"""

    ipython_tokens = [
        (r"(?s)(\s*)(%%capture)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?s)(\s*)(%%debug)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?is)(\s*)(%%html)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(HtmlLexer))),
        (
            r"(?s)(\s*)(%%javascript)([^\n]*\n)(.*)",
            bygroups(Text, Operator, Text, using(JavascriptLexer)),
        ),
        (r"(?s)(\s*)(%%js)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(JavascriptLexer))),
        (r"(?s)(\s*)(%%latex)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(TexLexer))),
        (r"(?s)(\s*)(%%perl)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PerlLexer))),
        (r"(?s)(\s*)(%%prun)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?s)(\s*)(%%pypy)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?s)(\s*)(%%python)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?s)(\s*)(%%python2)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PythonLexer))),
        (
            r"(?s)(\s*)(%%python3)([^\n]*\n)(.*)",
            bygroups(Text, Operator, Text, using(Python3Lexer)),
        ),
        (r"(?s)(\s*)(%%ruby)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(RubyLexer))),
        (r"(?s)(\s*)(%%time)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?s)(\s*)(%%timeit)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?s)(\s*)(%%writefile)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?s)(\s*)(%%file)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(PyLexer))),
        (r"(?s)(\s*)(%%)(\w+)(.*)", bygroups(Text, Operator, Keyword, Text)),
        (r"(?s)(^\s*)(%%!)([^\n]*\n)(.*)", bygroups(Text, Operator, Text, using(BashLexer))),
        (r"(%%?)(\w+)(\?\??)$", bygroups(Operator, Keyword, Operator)),
        (r"\b(\?\??)(\s*)$", bygroups(Operator, Text)),
        (r"(%)(sx|sc|system)(.*)(\n)", bygroups(Operator, Keyword, using(BashLexer), Text)),
        (r"(%)(\w+)(.*\n)", bygroups(Operator, Keyword, Text)),
        (r"^(!!)(.+)(\n)", bygroups(Operator, using(BashLexer), Text)),
        (r"(!)(?!=)(.+)(\n)", bygroups(Operator, using(BashLexer), Text)),
        (r"^(\s*)(\?\??)(\s*%{0,2}[\w\.\*]*)", bygroups(Text, Operator, Text)),
        (r"(\s*%{0,2}[\w\.\*]*)(\?\??)(\s*)$", bygroups(Text, Operator, Text)),
    ]

    tokens = PyLexer.tokens.copy()
    tokens["root"] = ipython_tokens + tokens["root"]

    attrs = {"name": name, "aliases": aliases, "filenames": [], "__doc__": doc, "tokens": tokens}

    return type(name, (PyLexer,), attrs)


IPython3Lexer = build_ipy_lexer(python3=True)
