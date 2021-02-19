import click
import typing


# import functools as ft


def option(*param_decls, **attrs):
    """`show_default = True`.

    If `default` in `attrs` and `type` is not, or vice versa, sets one based on the other.

    Unless `default = None`, in which case `type` isn't set.

    If both are missing, `type` defaults to `str`.


    `type` can be either:
     - type, i.e. `str`
     - tuple, i.e. `(str, int)`
     - `typing.Literal['foo']`
     - `click.typing.<Foo>` (which includes click.Choice(...))
    """
    attrs['show_default'] = True
    default = attrs.get('default', click.core._missing)
    default_is_missing = default is click.core._missing
    typeattr = attrs.get('type', click.core._missing)
    type_is_missing = typeattr is click.core._missing
    if not type_is_missing:
        if typing.get_origin(typeattr) is typing.Literal:
            # type=typing.Literal['foo']. build a click.Choice from it
            attrs['type'] = click.Choice(typeattr.__args__)
            if default_is_missing:
                # take first Literal arg
                attrs['default'] = typeattr.__args__[0]
        
        else:
            # not a typing.Literal (e.g. `type=str`)
            attrs['type'] = typeattr
            if default_is_missing:
                attrs['default'] = typeattr()
    
    else:
        # type is missing.
        # if default=None, it's probably just a placeholder and
        # doesn't tell us above the 'real' type
        if not default_is_missing and default is not None:
            attrs['type'] = type(default)
        # otherwise, type and default both missing. not sure if this works
    
    if attrs.get('metavar', click.core._missing) is click.core._missing \
            and attrs.get('type', click.core._missing) is not click.core._missing:
        try:
            # changes click's default "BOOLEAN" to "BOOL", "INTEGER" → "INT"
            attrs['metavar'] = attrs['type'].__name__.upper()
        except AttributeError:
            # has no attribute __name__
            pass
    return click.option(*param_decls, **attrs)


def unrequired_opt(*param_decls, **attrs):
    """`required = False, show_default = True`.

    If `default` in `attrs` and `type` is not, or vice versa, sets one based on the other.

    Unless `default = None`, in which case `type` isn't set.

    If both are missing, `type` defaults to `str`.

    `type` can be either:
     - type, i.e. `str`
     - tuple, i.e. `(str, int)`
     - `typing.Literal['foo']`
     - `click.typing.<Foo>` (which includes click.Choice(...))
    """
    
    attrs['required'] = False
    return option(*param_decls, **attrs)


def required_opt(*param_decls, **attrs):
    """`required = True, show_default = True`.

    If `default` in `attrs` and `type` is not, or vice versa, sets one based on the other.

    Unless `default = None`, in which case `type` isn't set.

    If both are missing, `type` defaults to `str`.

    `type` can be either:
     - type, i.e. `str`
     - tuple, i.e. `(str, int)`
     - `typing.Literal['foo']`
     - `click.typing.<Foo>` (which includes click.Choice(...))
    """
    
    attrs['required'] = True
    return option(*param_decls, **attrs)
