from typing import Iterable, List, Union

import re
import functools
import inspect

def return_none_if_errors(*exc):
    """If no `exc` specified, returns None on any exception.
    >>> @return_none_if_errors(ValueError)
    ... def raises(exc):
    ...     raise exc()
    >>> raises(ValueError) is None
    True
    >>> raises(TypeError)
    Traceback (most recent call last):
        ...
    TypeError
    >>> @return_none_if_errors
    ... def raises(exc):
    ...     raise exc()
    >>> raises(OverflowError) is None
    True
    """
    
    def wrap(fn):
        @functools.wraps(fn)
        def decorator(*fnargs, **fnkwargs):
            
            try:
                return fn(*fnargs, **fnkwargs)
            except exc:
                return None
        
        return decorator
    
    if not exc:
        # @return_none_if_errors()    (parens but no args)
        exc = Exception
    elif inspect.isfunction(exc[0]):
        # @return_none_if_errors    (naked)
        _fn = exc[0]
        exc = Exception
        return wrap(_fn)
    
    # @return_none_if_errors(ValueError)
    return wrap
@return_none_if_errors(ValueError, TypeError)
def safeslice(val: Union[str, int, slice]) -> slice:
    """Safe constructor for slice. Handles "2", "0:2", and ":2".
    Always returns a slice (or None if conversion fails).

    >>> mylist = ['first', 'second', 'third']
    >>> mylist[safeslice("1")] == mylist[safeslice(1)] == ['first']
    True

    >>> mylist[safeslice("0:2")] == mylist[safeslice(slice(0,2))] == ['first', 'second']
    True

    >>> mylist[safeslice(":2")] == mylist[safeslice(slice(2))] == ['first', 'second']
    True

    >>> safeslice("foo") is None
    True
    """
    
    def _to_slice(_val) -> slice:
        if isinstance(_val, slice):
            return _val
        # _stop = int(_val) + 1
        return slice(int(_val))  # may raise TypeError → None
    
    if isinstance(val, str):
        val = val.strip()
        if ':' in val:
            start, _, stop = val.partition(':')
            if start == '':  # ":2"
                start = 0
            return slice(int(start), int(stop))
    return _to_slice(val)


@return_none_if_errors(ValueError, TypeError)
def safeint(val: Union[str, int]) -> int:
    """Handles int and str ("1").
    Always returns an int (or None if cannot be used as a precise index).

    >>> mylist = ['first', 'second']
    >>> mylist[safeint("0")] == mylist[safeint(0)] == 'first'
    True

    >>> all(bad is None for bad in (safeint("0:2"), safeint(slice(0, 2)), safeint("foo")))
    True
    """
    
    if isinstance(val, str):
        val = val.strip()
    return int(val)  # may raise TypeError → None
def to_int_or_slice(val):
    """Tries converting to int, then to slice if fails.
    Finally returns None if converting to slice fails as well"""
    _int = safeint(val)
    if _int is not None:
        return _int
    _slice = safeslice(val)
    if _slice is not None:
        return _slice
    return None
def unquote(string) -> str:
    # TODO: "gallery is MOBILE only if <= $BP3" -> "gallery is MOBILE only if <=" (maybe bcz bash?)
    string = str(string)
    # content = quoted_content(string)
    # if content:
    #     return content.strip()
    # return string.strip()
    match = re.fullmatch(r'(["\'])(.*)\1', string, re.DOTALL)
    if match:  # "'hello'"
        string = match.groups()[1]
    return string.strip()
def clean(string: str) -> str:
    return unquote(string.strip())

def has_duplicates(collection) -> bool:
    return len(set(collection)) < len(collection)


def get_duplicates(collection: Iterable):
    uniq = set()
    duplicates = []
    for item in collection:
        if item in uniq:
            duplicates.append(item)
        else:
            uniq.add(item)
    return duplicates


def remove_duplicates(collection: Iterable) -> List:
    without_duplicates = []
    for item in collection:
        if item not in without_duplicates:
            without_duplicates.append(item)
    return without_duplicates


def difference(coll1: Iterable, coll2: Iterable) -> List:
    diff = []
    for item in coll1:
        if item not in coll2:
            diff.append(item)
    return diff


def intersection(coll1: Iterable, coll2: Iterable) -> List:
    inter = []
    for item in coll1:
        if item in coll2:
            inter.append(item)
    return inter
