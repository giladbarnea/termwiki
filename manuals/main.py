#!/usr/bin/env python3.8
"""
get_main_topics() is called to popuplate MAIN_TOPICS.
"""
import inspect
import logging
import re
import sys
# from functools import wraps
from typing import Callable, Union
from typing import Dict, List, Any, Tuple

import click
# from more_termcolor import cprint

# import search
# import prompt
from manuals.common.click_extension import unrequired_opt

# stuff from manuals.py to ignore when dir'ing manuals module
from manuals.common.types import ManFn


# brightprint = lambda s, *colors: cprint(s, 'bright white', *colors)
SUB_TOPIC_RE = re.compile(r'_[A-Z]*\s?=\s?(rf|fr|f)"""')
from rich.console import Console

console = Console()
EXCLUDE = [
    # imports
    'inspect',
    're',
    
    # functools
    'wraps',
    
    # typing
    'Literal',
    'Dict',
    'Type',
    'Union',
    
    # formatting
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'b',
    'c',
    'i',
    'black',
    'bg',
    'ManFn',
    
    # pygments
    'Lexer',
    'pyglight',
    'TerminalTrueColorFormatter',
    'get_lexer_by_name',
    'BashLexer',
    'CssLexer',
    'DockerLexer',
    'IniLexer',
    'JavascriptLexer',
    'JsonLexer',
    'MySqlLexer',
    'PythonLexer',
    'SassLexer',
    'TypeScriptLexer',
    
    # module-level vars
    'linebreak',
    'backslash',
    # 'color',
    'Style',
    'Language',
    'langs',
    'HIGHLIGHT_START_RE',
    'HIGHLIGHT_END_RE',
    'formatters',
    'lexers',
    
    # functions
    '_get_lexer_ctor',
    '_get_lexer',
    '_get_color_formatter',
    '_highlight',
    'alias',
    'syntax',
    
    # module magics
    '__annotations__',
    '__builtins__',
    '__cached__',
    '__doc__',
    '__file__',
    '__loader__',
    '__name__',
    '__package__',
    '__spec__'
    ]
# perform_checks = any(arg == '--check' for arg in sys.argv)


# module = dict(igit=dict())


# # noinspection PyUnresolvedReferences
# # This is only called by itself right now, no actual usage
# def fromigit(dotnames, igitmod=None, module_subdict: dict = None):
#     """
#     Examples
#     ::
#         fromigit('prompt')
#         fromigit('prompt.Flow')
#         fromigit('util.clickex.unrequired_opt')
#     """
#     # TODO: IMPLEMENT
#     #  the goal is to avoid actual import as much as possible
#     #  so that `module` stores only dicts if not used directly, e.g. 'util' can be a { 'clickex': {'unrequired_opt': unrequired_opt} } where
#     #  only unrequired_opt is a function.
#     #  it's tricky because 'prompt' can be used directly e.g. prompt.choose, or indirectly e.g. prompt.Flow.CONTINUE
#     #  need to decide, if I allow fromigit('prompt').choose then fromigit('prompt') must be a module and not a dict.
#     #  in which case, how to avoid importing too much when fromigit('prompt.Flow')?
#
#     ## possible scenarios:
#     # dotnames = 'prompt', igitmod = None, module_subdict = None →
#     #   dotnames = 'prompt', igitmod = igit, module_subdict = module['igit'] →
#
#     # dotnames = 'prompt.Flow', igitmod = None, module_subdict = None →
#     #   dotnames = 'prompt.Flow', igitmod = igit, module_subdict = module['igit'] →
#
#     # dotnames = 'util.clickex.unrequired_opt', igitmod = None, module_subdict = None →
#
#     if module_subdict is None:
#         # assuming igitmod is None also
#         import igit
#         return fromigit(dotnames, igitmod=igit, module_subdict=module['igit'])
#
#     name, _, nestednames = dotnames.partition('.')
#     cachedval = module_subdict.get(name)
#     if cachedval is None:
#         nestedmod = getattr(igitmod, name)  # actual import, so nestedmod may be prompt
#         module_subdict[name] = dict()  # initialize e.g. module['igit']['prompt'] = prompt
#
#         if nestednames:
#             # e.g. nestednames='clickex.unrequired_opt'; nestedmod=util; module_subdict[name]=dict()
#             val = fromigit(nestednames, igitmod=nestedmod, module_subdict=module_subdict[name])
#         else:
#             # this is it
#             val = nestedmod
#             module_subdict[name] = val
#             return val
#
#     else:
#         ## cachedval is a dict
#         if nestednames:
#             # e.g. nestednames = 'Flow', cachedval = module['igit']['prompt']
#             val = fromigit(nestednames, igitmod=nestedmod, module_subdict=module_subdict[name])
#         else:
#             # e.g. cachedval = module['igit']['prompt']
#             return cachedval
#         val = nestedmod
#     if first_recursion:
#         module[nestednames] = val
#     if not val:
#         errmsg = (f"fromigit(dotnames: '{dotnames}', igitmod: {igitmod}) | "
#                   "locals:"
#                   f"{locals()}"
#                   )
#         raise ModuleNotFoundError(errmsg)
#     return val


# def logger() -> ForwardRef('Loggr'):
#     _logger = module.get('logger')
#     if _logger is not None:
#         return _logger
#     # 'logger' not in module; construct one
#     IGIT_LOG_LEVEL = os.environ.get('IGIT_LOG_LEVEL', '')
#     if IGIT_LOG_LEVEL.lower() == 'none':
#         class Loggr:
#             def __init__(self, *args, **kwargs):
#                 pass
#
#             def __getattribute__(self, item):
#                 return self
#
#             def __call__(self, *args, **kwargs):
#                 return self
#
#     else:
#         print('myman.py importing igit_debug Loggr')
#         from igit_debug.loggr import Loggr
#     module['logger'] = Loggr(__name__)
#     return module['logger']


# used by print_manual()
# def printrv(fn):
#     @wraps(fn)
#     def wrap(*args, **kwargs):
#         rv = fn(*args, **kwargs)
#         print(rv)
#         return rv
#
#     return wrap


def create_new_manual(newtopic: str):  # called in __main__.py
    logging.debug(f'create_new_manual({newtopic = })')
    if newtopic.lower() in map(str.lower, MAIN_TOPICS):
        logging.warning(f"{newtopic = } already exists")
        return False
    logging.warning('should not be implemented, dont be lazy')
    # from mytool.myman import manuals
    # print(f"creating {newtopic} in {manuals.__file__}...")
    # with open(manuals.__file__, mode='r+') as manfile:

def get_skipped_subtopics(undecorated_main_topic_fn):
    """python3.8 -m mytool.myman --check calls this"""
    lines = inspect.getsource(undecorated_main_topic_fn).splitlines()
    last_else_idx = -next(i for i, line in enumerate(reversed(lines)) if line.strip() == 'else:') - 1
    before_else = [line.strip().partition('=')[0].strip() for line in lines[:last_else_idx] if
                   line and SUB_TOPIC_RE.search(line)]
    after_else = [line.strip()[1:-1] for line in lines[last_else_idx:] if
                  (stripped := line.strip()).startswith('{_') and stripped.endswith('}')]
    if diff := set(before_else).difference(set(after_else)):
        logging.warning(f'{undecorated_main_topic_fn.__name__}() doesnt print: {diff}')


def draw_out_decorated_fn(fn: ManFn) -> Callable:
    closure: tuple = fn.__closure__
    if not closure:
        # non-decorated functions' closure is None
        return fn
    return closure[-1].cell_contents


def populate_main_topics() -> Dict[str, ManFn]:
    """Populates a { 'pandas' : pandas , 'inspect' : inspect_, 'gh' : githubcli } dict from `manuals` module"""
    from . import manuals
    main_topics = dict()
    for main_topic in dir(manuals):
        if main_topic in EXCLUDE:
            continue
        fn: Callable = getattr(manuals, main_topic)
        if not inspect.isfunction(fn):
            continue
        # noinspection PyUnresolvedReferences
        if not fn.__module__.endswith('.manuals') or 'Lexer' in main_topic:
            # This happens when something is missing in EXCLUDE, oversight from my part
            continue
        if main_topic.endswith('_'):  # inspect_()
            name = main_topic[:-1]
        else:
            name = main_topic
        # * dont draw_out_decorated_fn because then syntax() isn't called
        main_topics[name] = fn
        try:
            alias = getattr(fn, 'alias')
        except:
            pass
        else:
            main_topics[alias] = fn
    
    return main_topics


MAIN_TOPICS: Dict[str, ManFn] = populate_main_topics()


def get_sub_topic_var_names(fn: ManFn) -> List[str]:
    return [n for n in fn.__code__.co_varnames if n.isupper()]


def populate_sub_topics(*, print_skipped_subtopics=False) -> Dict[str, Union[List[ManFn], ManFn]]:
    """Sets bash.sub_topics = [ "cut" , "for" ] for each MAIN_TOPICS.
    Removes (d)underscore and lowers _CUT and __FOR.
    Returns e.g. `{ 'cut' : bash , 'args' : [ bash , pdb ] }`"""
    # var_reg = r'_[A-Z0-9_]*'
    # matches `_SUBTOPIC = fr"""..."""` and `_ST = _SUBTOPIC`
    # sub_topic_reg = re.compile(fr'\s*{var_reg}\s?=\s?(r?fr?""".*|{var_reg})\n')
    # subject_sig_re = re.compile(r'subject\s?=\s?None')
    
    sub_topics = dict()
    # populate sub topics as main_topics
    # global perform_checks
    for main_topic_fn in list(MAIN_TOPICS.values()):
        
        # sub_topic_var_names = [n for n in draw_out_decorated_fn(main_topic_fn).__code__.co_varnames if n.isupper()]
        # draw_out_decorated_fn is necessary because MAIN_TOPICS has to store the fns in the wrapped form (to call them later)
        setattr(main_topic_fn, 'sub_topics', [])
        undecorated_main_topic_fn = draw_out_decorated_fn(main_topic_fn)
        sub_topic_var_names = get_sub_topic_var_names(undecorated_main_topic_fn)
        if not sub_topic_var_names:
            continue
        # lines, _ = inspect.getsourcelines(main_topic_fn)
        # if not re.search(subject_sig_re, lines[0]) and not re.search(subject_sig_re, lines[1]):
        # lines[1]: decorated functions' first line is the @decorator
        # if not 'subject' in inspect.getfullargspec(main_topic_fn).args:
        #     continue
        
        # lines = [l.strip() for l in lines if re.fullmatch(sub_topic_reg, l)]
        # if not lines:  # has subject=None in sig but no actual sub topic vars
        #     continue
        
        if print_skipped_subtopics:
            print(get_skipped_subtopics(undecorated_main_topic_fn))
        
        for sub_topic_var_name in sub_topic_var_names:
            # DONT account for dunder __ARGUMENTS, it's being handled by get_sub_topic().
            # If handled here, eventually bash('_ARGUMENTS') is called which errors.
            # if (stripped := sub_topic_var_name.strip()).startswith('__'):
            #     sub_topic_var_name = stripped.lower()[2:]
            # else:  # starts with single '_'
            #     sub_topic_var_name = stripped.lower()[1:]
            sub_topic_var_name = sub_topic_var_name.strip().lower()[1:]
            main_topic_fn.sub_topics.append(sub_topic_var_name)
            if sub_topic_var_name in sub_topics:
                # this means duplicate subtopic, for different main topics
                # in that case, the value is set to be a list of subtopics
                if isinstance(sub_topics[sub_topic_var_name], list):
                    sub_topics[sub_topic_var_name].append(main_topic_fn)
                else:
                    # create a new list
                    sub_topics[sub_topic_var_name] = [sub_topics[sub_topic_var_name], main_topic_fn]
            else:
                # no duplicate sub topics; value is set to be simply the function
                sub_topics[sub_topic_var_name] = main_topic_fn
    
    return sub_topics


SUB_TOPICS: Dict[str, Union[List[ManFn], ManFn]] = populate_sub_topics()


def fuzzy_find_topic(topic, collection, *extra_opts, raise_if_exhausted=False, **extra_kw_opts) -> Tuple:
    """If user continue'd through the whole collection, raises KeyError if `raise_if_exhausted` is True. Otherwise, returns None"""
    # not even a subtopic, could be gibberish
    # try assuming it's a substring
    import search
    import prompt
    for maybes, is_last in search.iter_maybes(topic, collection, criterion='substring'):
        if not maybes:
            continue
        
        kwargs = dict(Ep='Edit manuals.py with pycharm', Ec='Edit manuals.py with vscode',
                      Em='Edit manuals.py with micro')
        
        if is_last and raise_if_exhausted:
            kwargs.update(dict(flowopts='quit'))
        else:
            kwargs.update(dict(flowopts='quit', no='continue'))
        # TODO: if a match is a subtopic, present maintopic.subtopic in choose
        key, choice = prompt.choose(f"Did you mean any of these?", *extra_opts, *maybes, **kwargs,
                                    **extra_kw_opts)
        if choice == prompt.Flow.CONTINUE:
            continue
        if isinstance(key, str) and key.startswith('E'):
            import os
            manualsfile = os.path.join(os.path.dirname(__file__), 'manuals.py')
            if key == 'Ep':
                os.system(f'pycharm "{manualsfile}"')
            if key == 'Ec':
                os.system(f'code "{manualsfile}"')
            if key == 'Em':
                os.system(f'micro "{manualsfile}"')
            sys.exit()
        return key, choice.value
    if raise_if_exhausted:
        raise KeyError(f"'{topic}' isn't in collection")
    return None, None


def get_sub_topic(main_topic: str, sub_topic: str):
    """
    MAIN EXISTS?
     |      \
    yes     no
     |       \
     |      [find main]
     |        |     \
     |      found   nope
     |       /        \
     |     /        KeyError!
     |   /
    SUB IN MAIN's SUBS?
     |          \
    yes         no
     |           \
    [return]    [find sub in main's]
                   |         \
                found       nope
                  |           \
                [return]    SUB IN ANY MAIN's SUBS?
                              |         \
                            yes         no
                             |           \
                            [return]    [find sub]
                                          |       \
                                        found      nope
                                          |         \
                                        [return]   KeyError!
    """
    logging.debug(f"get_sub_topic({repr(main_topic)}, {repr(sub_topic)})")
    if main_topic not in MAIN_TOPICS:
        console.log(f"[bright_white]Unknown main topic: '{main_topic}'. Searching among MAIN_TOPICS...[/]")
        # brightprint(f"Unknown main topic: '{main_topic}'. Searching among MAIN_TOPICS...")
        main_topic = fuzzy_find_topic(main_topic, MAIN_TOPICS, raise_if_exhausted=True)
    
    main_topic_fn: ManFn = MAIN_TOPICS[main_topic]
    if sub_topic in main_topic_fn.sub_topics:
        return main_topic_fn(f'_{sub_topic.upper()}')
    if f'_{sub_topic}' in main_topic_fn.sub_topics:
        # mm bash syntax → main_topic_fn.sub_topics has '_syntax' → pass '__SYNTAX'
        return main_topic_fn(f'__{sub_topic.upper()}')
    
    try:
        # sometimes functions have alias logic under 'if subject:' clause, for example bash
        # has 'subject.startswith('<')'. so maybe sub_topic works
        return main_topic_fn(sub_topic)
    except KeyError:
        console.log((f"[bright_white]sub topic '{sub_topic}' isn't a sub topic of '{main_topic}'. "
                     f"Searching among '{main_topic}'s sub topics...[/]"))
        key, chosen_sub_topic = fuzzy_find_topic(sub_topic,
                                                 main_topic_fn.sub_topics,
                                                 raise_if_exhausted=False,
                                                 # keep uppercase P so doesn't collide with topics
                                                 P=f"print '{main_topic}' w/o subtopic")
        if key == 'P':
            return main_topic_fn()
        
        if chosen_sub_topic is not None:
            return main_topic_fn(f'_{chosen_sub_topic.upper()}')
        
        if sub_topic in SUB_TOPICS:
            console.log(f"[bright_white]'{sub_topic}' isn't a sub topic of '{main_topic}', but it belongs to these topics:[/]")
            return print_manual(sub_topic)
        
        console.log(f"[bright_white]'{sub_topic}' doesn't belong to any topic. Searching among all SUB_TOPICS...[/]")
        key, sub_topic = fuzzy_find_topic(sub_topic,
                                          SUB_TOPICS,
                                          raise_if_exhausted=True,
                                          P=f"print '{main_topic}' w/o subtopic")
        if key == 'P':
            return main_topic_fn()
        
        return main_topic_fn(f'_{sub_topic.upper()}')


def print_manual(main_topic: str, sub_topic=None):
    """If passed correct topic(s), prints.
    If not correct, finds the correct with fuzzy search and calls itself."""
    logging.debug(f"print_manual({repr(main_topic)}, {repr(sub_topic)})")
    if sub_topic:
        # * passed both main, sub
        sub_topic_str = get_sub_topic(main_topic, sub_topic)
        # sub_topic_str = get_sub_topic(main_topic, sub_topic) \
        #     .replace('[h1]', '[bold underline reverse bright_white]') \
        #     .replace('[h2]', '[bold underline bright_white]') \
        #     .replace('[h3]', '[bold bright_white]') \
        #     .replace('[h4]', '[bright_white]') \
        #     .replace('[h5]', '[white]') \
        #     .replace('[c]', '[dim]')
        # return console.print(sub_topic_str)
        return print(sub_topic_str)
    # ** passed only one arg, could be main or sub
    try:
        # * assume precise main topic, i.e. "git"
        return print(MAIN_TOPICS[main_topic]())
    except KeyError as not_main_topic:
        # * so maybe it's a precise sub topic, i.e. "diff"
        topic = main_topic
        try:
            fn: Callable[[str], Any] = SUB_TOPICS[topic]
        except KeyError as not_sub_topic_not_main_topic:
            # * not a precise subtopic. find something precise, either a main or sub topic
            key, topic = fuzzy_find_topic(topic,
                                          list(MAIN_TOPICS.keys()) + list(SUB_TOPICS.keys()),
                                          raise_if_exhausted=True)
            return print_manual(topic)
        else:
            # * indeed a precise subtopic, call the main topic's fn and pass subtopic param
            try:
                return print(fn(f'_{topic.upper()}'))
            except TypeError as duplicate_sub_topic:
                # * error: "'list' object is not callable". some topics share same subtopic. choose main topic
                import prompt
                fn: List[Callable[[str], Any]]
                
                # TODO (bugs): 
                #  (1) If an ALIAS of a subtopic is the same as a SUBTOPIC of another main topic,
                #    this is called (shouldn't). Aliases aren't subtopics. (uncomment asyncio # _SUBPROCESS = _SUBPROCESSES)
                #  (2) main topics with both @alias and @syntax decors, that have the issue above ("(1)"), raise
                #    a ValueError in igit prompt, because the same main topic function is passed here for each subtopic and subtopic alias.
                #  ValueError: ('NumOptions | __init__(opts) duplicate opts: ', ('<function asyncio at 0x7f5dab684ca0>', '<function asyncio at 0x7f5dab684ca0>', '<function python at 0x7f5dab669a60>'))
                idx, choice = prompt.choose(f"'{topic}' exists in several topics, which one did you mean?",
                                            *[f.__qualname__ for f in fn],
                                            flowopts='quit'
                                            )
                return print(fn[idx](f'_{topic.upper()}'))





@click.command(context_settings=dict(help_option_names=['-h', '--help']), help="--check is also possible")
@click.argument('main_topic')
@click.argument('sub_topic', required=False)
@unrequired_opt('-l', '--list', 'list_subtopics', is_flag=True, help='list sub topics')
@unrequired_opt('--doctor', 'print_skipped_subtopics', is_flag=True, help="prints any subtopics that are skipped erroneously in a main topic's else clause")
def get_topic(main_topic, sub_topic, list_subtopics, print_skipped_subtopics):
    logging.debug(f'myman.get_topic({main_topic = }, {sub_topic = }, {list_subtopics = })')
    if print_skipped_subtopics:
        populate_sub_topics(print_skipped_subtopics=True)
        return
    if list_subtopics:
        console.log(f"[bright_white bold underline]{main_topic}[/]\n")
        [print(f'{st}') for st in sorted(MAIN_TOPICS[main_topic].sub_topics)]
        return
    
    print_manual(main_topic, sub_topic)
