import ast
import inspect
from collections.abc import Generator
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Callable, ParamSpec

from termwiki.consts import NON_LETTER_RE, PROJECT_ROOT_PATH
from termwiki.log import log

ParamSpec = ParamSpec('ParamSpec')


def normalize_page_name(page_name: str) -> str:
    return NON_LETTER_RE.sub('', page_name).lower()


def import_module_by_path(path: Path) -> ModuleType:
    if path.is_relative_to(PROJECT_ROOT_PATH):
        python_module_relative_path = path.relative_to(PROJECT_ROOT_PATH)
    else:
        python_module_relative_path = path
    python_module_name = '.'.join(python_module_relative_path.with_suffix('').parts)
    imported_module = import_module(python_module_name)
    return imported_module


def pformat_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    return ast.dump(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent).replace(r'\n', '\n... ')


def pprint_node(node: ast.AST, annotate_fields=True, include_attributes=False, indent=4):
    print(pformat_node(node, annotate_fields=annotate_fields, include_attributes=include_attributes, indent=indent))


def get_local_var_names_inside_joined_str(joined_str: ast.JoinedStr) -> list[str]:
    var_names = []
    for formatted_value in joined_str.values:
        if isinstance(formatted_value, ast.FormattedValue) \
                and isinstance(formatted_value.value, ast.Name):
            # We care only about {local_var} fstrings, aka formatted_value.value: ast.Name
            # because anything else (ast.Call etc) is found in globals_
            # todo: this is not true if joined_str is module-level variable!
            var_names.append(formatted_value.value.id)
    return var_names


def get_local_variables(joined_str: ast.JoinedStr,
                        parent: Callable[ParamSpec, str],
                        globals_: dict,
                        ) -> dict:
    isinstance(joined_str, ast.JoinedStr) or breakpoint()
    local_var_names_in_fstring = get_local_var_names_inside_joined_str(joined_str)
    local_var_names_in_fstring or breakpoint()
    local_variables = dict.fromkeys(local_var_names_in_fstring)
    # In terms of reuse, FunctionPage.python_module_ast() also does this
    # traverse_assign_node(source_node, parent)
    source_parent_node: ast.Module = ast.parse(inspect.getsource(parent))
    source_node = source_parent_node.body[0]
    if isinstance(source_node, ast.FunctionDef):
        for assign in source_node.body:
            if not isinstance(assign, ast.Assign):
                continue
            for target in assign.targets:
                if target.id in local_var_names_in_fstring:
                    var_value = eval_node(assign.value, parent, globals_)
                    local_variables[target.id] = var_value
    elif isinstance(source_node, ast.Assign):
        # breakpoint()
        for var_name, var_value in traverse_assign_node(source_node, parent):
            local_variables[var_name] = var_value
    elif isinstance(source_node, ast.ImportFrom):
        # untested! wrote quickly
        for alias in source_node.names:
            if alias.asname:
                var_name = alias.asname
            else:
                var_name = alias.name
            var_value = getattr(parent, var_name)
            local_variables[var_name] = var_value
    else:
        breakpoint()
        raise NotImplementedError(f'get_local_variables(...)\n\t{source_node=}'
                                  f'\n\tnot FunctionDef, not Assign nor ImportFrom\n\t{source_parent_node=}'
                                  f'\n\t{parent=}')
    return local_variables


def eval_node(node, parent, globals_):
    try:
        unparsed_value = ast.unparse(node)
        try:
            evaled: str = eval(unparsed_value, globals_)
        except NameError as e:
            # This happens when the value is composed of other local variables
            #  within the same function. E.g the value is "f'{x}'", and x is a local variable.
            #  'x' isn't in the globals, so it's a NameError.
            #  We're resolving the values of the composing local variables.

            locals_ = get_local_variables(node, parent, globals_)
            evaled = eval(unparsed_value, globals_, locals_)
        return evaled
    except Exception as e:
        print(e)
        breakpoint()


def traverse_immutable_when_unparsed(node, parent, target_id):
    """JoinedStr, Constant, Name, FormattedValue, or sometimes even a simple Expr,
    when ast.unparse(node) returns a string that can be evaluated and used as-is."""
    from . import VariablePage
    if hasattr(parent, '__globals__'):
        assert callable(parent) and not isinstance(parent, ModuleType), f'{parent} is not a function'
        globals_ = parent.__globals__
    elif isinstance(parent, ModuleType):
        globals_ = {var:val for var,val in vars(parent).items() if not var.startswith('__')} # todo: more specific, also think about module-level alias etc
    elif hasattr(parent, '__builtins__'):
        assert not callable(parent), f'{parent} is a callable'
        globals_ = parent.__builtins__
    else:
        raise AttributeError(f'traverse_immutable_when_unparsed(\n\t{node=},\n\t{parent=},\n\t{target_id=}): '
                             f'parent has neither __globals__ nor is it a ModuleType, not does it have __builtins__.\n\t{type(parent) = }')
    rendered = eval_node(node.value, parent, globals_)
    yield target_id, VariablePage(rendered, target_id)


def traverse_assign_node(node: ast.Assign, parent: Callable[ParamSpec, str] | ModuleType) -> Generator[tuple[str, "VariablePage"]]:
    from . import VariablePage
    parent = inspect.unwrap(parent)  # parent isn't necessarily a function, but that's ok
    target: ast.Name
    for target in node.targets:
        target_id = normalize_page_name(target.id)
        if isinstance(node.value, ast.Constant):
            yield target_id, VariablePage(node.value.value, target_id)
        else:
            yield from traverse_immutable_when_unparsed(node, parent, target_id)


def traverse_function(function: Callable[ParamSpec, str], python_module_ast: ast.Module) -> Generator[tuple[str, "VariablePage"]]:
    # noinspection PyTypeChecker
    function_def_ast: ast.FunctionDef = python_module_ast.body[0]
    for node in function_def_ast.body:
        if isinstance(node, ast.Assign):
            yield from traverse_assign_node(node, function)
        else:
            assert hasattr(node, 'value'), f'{node} has no value attribute' or breakpoint()
            yield from traverse_immutable_when_unparsed(node, function, function_def_ast.name)  # note: when node is ast.Return, function_def_ast.name is the function name


def traverse_module(module: ModuleType, python_module_ast: ast.Module):
    from . import FunctionPage
    exclude_names = getattr(module, '__exclude__', {})
    for node in python_module_ast.body:
        if hasattr(node, 'name'):
            node_name = normalize_page_name(node.name)
            if node.name in exclude_names or node_name in exclude_names:
                continue
            if isinstance(node, ast.FunctionDef):
                function = getattr(module, node.name)
                yield node_name, FunctionPage(function)

                # this will be replaced with import hook
                if hasattr(function, 'aliases'):
                    for alias in function.aliases:
                        yield normalize_page_name(alias), FunctionPage(function)
            else:
                log.warning(f'traverse_module({module}): {node} has "name" but is not a FunctionDef')
                breakpoint()
            continue
        if hasattr(node, 'names'):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            log.warning(f'traverse_module({module}): {node} has "names" but is not an Import or ImportFrom')
            breakpoint()
            for alias in node.names:
                if alias.name not in exclude_names:
                    yield alias.name, getattr(module, alias.name)
            continue
        if isinstance(node, ast.Assign):
            yield from traverse_assign_node(node, module)
            continue
        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant):
                node_value = node.value.value
                if module.__doc__ == node_value:
                    # yield '__doc__', VariablePage(node_value, '__doc__')
                    continue

        log.warning(f"traverse_module({module}): {node} doesn't have 'name' nor 'names', and is not an Assign nor an Expr for module.__doc__")
        breakpoint()
