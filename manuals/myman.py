#!/usr/bin/env python3.8
import inspect
import re
import sys
from functools import wraps
from typing import Dict, List, Union, Callable, Any, Tuple

import click
from igit import prompt
from igit import search
from igit.util.clickex import unrequired_opt

from more_termcolor import cprint

from mytool.tipes import ManFn

EXCLUDE = [
    # imports
    'inspect',
    're',
    'wraps',
    'Literal',
    'Dict',
    'Type',
    'Lexer',
    'h1',
    'h2',
    'h3',
    'h4',
    'b',
    'c',
    'i',
    'black',
    'ManFn',
    'pyglight',
    'TerminalTrueColorFormatter',
    'MySqlLexer',
    'PythonLexer',
    'CssLexer',
    'TypeScriptLexer',
    'BashLexer',
    'IniLexer',
    'get_lexer_by_name',
    'JsonLexer',
    'JavascriptLexer',
    
    # vars
    'newline',
    'backslash',
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
    'highlight',
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
brightprint = lambda s, *colors: cprint(s, 'bright white', *colors)
sub_topic_re = re.compile(r'_[A-Z]*\s?=\s?(rf|fr|f)"""')
perform_checks = any(arg == '--check' for arg in sys.argv)
module = dict(igit=dict())


def fromigit(dotnames, igitmod=None, module_subdict: dict = None):
    """
    Examples
    ::
        fromigit('prompt')
        fromigit('prompt.Flow')
        fromigit('util.clickex.unrequired_opt')
    """
    # TODO: IMPLEMENT
    #  the goal is to avoid actual import as much as possible
    #  so that `module` stores only dicts if not used directly, e.g. 'util' can be a { 'clickex': {'unrequired_opt': unrequired_opt} } where
    #  only unrequired_opt is a function.
    #  it's tricky because 'prompt' can be used directly e.g. prompt.choose, or indirectly e.g. prompt.Flow.CONTINUE
    #  need to decide, if I allow fromigit('prompt').choose then fromigit('prompt') must be a module and not a dict.
    #  in which case, how to avoid importing too much when fromigit('prompt.Flow')?
    
    ## possible scenarios:
    # dotnames = 'prompt', igitmod = None, module_subdict = None →
    #   dotnames = 'prompt', igitmod = igit, module_subdict = module['igit'] →
    
    # dotnames = 'prompt.Flow', igitmod = None, module_subdict = None →
    #   dotnames = 'prompt.Flow', igitmod = igit, module_subdict = module['igit'] →
    
    # dotnames = 'util.clickex.unrequired_opt', igitmod = None, module_subdict = None →
    
    if module_subdict is None:
        # assuming igitmod is None also
        import igit
        return fromigit(dotnames, igitmod=igit, module_subdict=module['igit'])
    
    name, _, nestednames = dotnames.partition('.')
    cachedval = module_subdict.get(name)
    if cachedval is None:
        nestedmod = getattr(igitmod, name)  # actual import, so nestedmod may be prompt
        module_subdict[name] = dict()  # initialize e.g. module['igit']['prompt'] = prompt
        
        if nestednames:
            # e.g. nestednames='clickex.unrequired_opt'; nestedmod=util; module_subdict[name]=dict()
            val = fromigit(nestednames, igitmod=nestedmod, module_subdict=module_subdict[name])
        else:
            # this is it
            val = nestedmod
            module_subdict[name] = val
            return val
    
    else:
        ## cachedval is a dict
        if nestednames:
            # e.g. nestednames = 'Flow', cachedval = module['igit']['prompt']
            val = fromigit(nestednames, igitmod=nestedmod, module_subdict=module_subdict[name])
        else:
            # e.g. cachedval = module['igit']['prompt']
            return cachedval
        val = nestedmod
    if first_recursion:
        module[nestednames] = val
    if not val:
        errmsg = (f"fromigit(dotnames: '{dotnames}', igitmod: {igitmod}) | "
                  "locals:"
                  f"{locals()}"
                  )
        raise ModuleNotFoundError(errmsg)
    return val


def logger() -> 'Loggr':
    _logger = module.get('logger')
    if _logger is not None:
        return _logger
    
    # 'logger' not in module; construct one
    from igit_debug.loggr import Loggr
    module['logger'] = Loggr(__name__)
    return module['logger']


def printrv(fn):
    @wraps(fn)
    def wrap(*args, **kwargs):
        rv = fn(*args, **kwargs)
        print(rv)
        return rv
    
    return wrap


def draw_out_decorated_fn(fn: ManFn):
    closure: tuple = fn.__closure__
    if not closure:
        # non-decorated functions' closure is None
        return fn
    
    return closure[-1].cell_contents


def get_main_topics() -> Dict[str, ManFn]:
    # (dict of functions)
    from mytool.myman import manuals
    main_topics = dict()
    for main_topic in dir(manuals):
        if main_topic in EXCLUDE:
            continue
        fn: Callable = getattr(manuals, main_topic)
        if not inspect.isfunction(fn):
            continue
        # noinspection PyUnresolvedReferences
        if not fn.__module__.endswith('.manuals'):
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


def get_sub_topic_var_names(fn: ManFn) -> List[str]:
    return [n for n in fn.__code__.co_varnames if n.isupper()]


MAIN_TOPICS: Dict[str, ManFn] = get_main_topics()


def check_unprinted_subtopics(undecorated_main_topic_fn):
    """python3.8 -m mytool.myman --check calls this"""
    lines = inspect.getsource(undecorated_main_topic_fn).splitlines()
    last_else_idx = -next(i for i, line in enumerate(reversed(lines)) if line.strip() == 'else:') - 1
    before_else = [line.strip().partition('=')[0].strip() for line in lines[:last_else_idx] if
                   line and sub_topic_re.search(line)]
    after_else = [line.strip()[1:-1] for line in lines[last_else_idx:] if
                  (stripped := line.strip()).startswith('{_') and stripped.endswith('}')]
    if diff := set(before_else).difference(set(after_else)):
        print(f'{undecorated_main_topic_fn.__name__}() doesnt print: {diff}')


def get_sub_topics() -> Dict[str, Union[List[ManFn], ManFn]]:
    """Returns e.g. `{ 'diff' : git }`"""
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
        # main_topic_fn.sub_topics = []
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
        
        if perform_checks:
            check_unprinted_subtopics(undecorated_main_topic_fn)
        
        for sub_topic_var_name in sub_topic_var_names:
            sub_topic_var_name = sub_topic_var_name.strip().lower()[1:]
            
            main_topic_fn.sub_topics.append(sub_topic_var_name)
            if sub_topic_var_name in sub_topics:
                # duplicate subtopic, different functions
                # in that case, the value is set to be a list of subtopics
                if isinstance(sub_topics[sub_topic_var_name], list):
                    sub_topics[sub_topic_var_name].append(main_topic_fn)
                else:
                    # create a new list
                    sub_topics[sub_topic_var_name] = [sub_topics[sub_topic_var_name], main_topic_fn]
            else:
                # value is set to be simply the function if no duplicates
                sub_topics[sub_topic_var_name] = main_topic_fn
    
    return sub_topics


SUB_TOPICS: Dict[str, Union[List[ManFn], ManFn]] = get_sub_topics()


def fuzzy_find_topic(topic, collection, *extra_opts, raise_if_exhausted=False, **extra_kw_opts) -> Tuple:
    """If user continue'd through the whole collection, raises KeyError if `raise_if_exhausted` is True. Otherwise, returns None"""
    # not even a subtopic, could be gibberish
    # try assuming it's a substring
    
    for maybes, is_last in search.iter_maybes(topic, collection, criterion='substring'):
        if not maybes:
            continue
        kwargs = dict(E='Edit manuals.py with pycharm')
        if is_last and raise_if_exhausted:
            kwargs.update(dict(flowopts='quit'))
        else:
            kwargs.update(dict(flowopts='quit', no='continue'))
        # TODO: if a match is a subtopic, present maintopic.subtopic in choose
        key, choice = prompt.choose(f"Did you mean any of these?", *extra_opts, *maybes, **kwargs,
                                    **extra_kw_opts)
        if choice == prompt.Flow.CONTINUE:
            continue
        if key == 'E':
            import os
            manualsfile = os.path.join(os.path.dirname(__file__), 'manuals.py')
            os.system(f'pycharm "{manualsfile}"')
            sys.exit()
        return key, choice.value
    if raise_if_exhausted:
        raise KeyError(f"'{topic}' isn't in collection")
    return None, None


def print_sub_topic(main_topic: str, sub_topic: str):
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
    logger().title(f"print_sub_topic({repr(main_topic)}, {repr(sub_topic)})")
    if main_topic not in MAIN_TOPICS:
        brightprint(f"Unknown main topic: '{main_topic}'. Searching among MAIN_TOPICS...")
        main_topic = fuzzy_find_topic(main_topic, MAIN_TOPICS, raise_if_exhausted=True)
    
    main_topic_fn = MAIN_TOPICS[main_topic]
    if sub_topic in main_topic_fn.sub_topics:
        return main_topic_fn(f'_{sub_topic.upper()}')
    if f'_{sub_topic}' in main_topic_fn.sub_topics:
        # bash syntax → main_topic_fn.sub_topics has '_syntax' → pass '__SYNTAX'
        return main_topic_fn(f'__{sub_topic.upper()}')
    
    try:
        # sometimes functions have alias logic under 'if subject:' clause, for example bash
        # has 'subject.startswith('<')'. so maybe sub_topic works
        
        return main_topic_fn(sub_topic)
    except KeyError:
        brightprint((f"sub topic '{sub_topic}' isn't a sub topic of '{main_topic}'. "
                     f"Searching among '{main_topic}'s sub topics..."))
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
            brightprint(f"'{sub_topic}' isn't a sub topic of '{main_topic}', but it belongs to these topics:")
            return print_topic(sub_topic)
        
        brightprint(f"'{sub_topic}' doesn't belong to any topic. Searching among all SUB_TOPICS...")
        key, sub_topic = fuzzy_find_topic(sub_topic,
                                          SUB_TOPICS,
                                          raise_if_exhausted=True,
                                          P=f"print '{main_topic}' w/o subtopic")
        if key == 'P':
            return main_topic_fn()
        
        return main_topic_fn(f'_{sub_topic.upper()}')


@printrv
def print_topic(main_topic: str, sub_topic=None):
    """If passed correct topic(s), prints.
    If not correct, finds the correct with fuzzy search and calls itself."""
    logger().title(f"print_topic({repr(main_topic)}, {repr(sub_topic)})")
    if sub_topic:
        # * passed both main, sub
        return print_sub_topic(main_topic, sub_topic)
    
    # ** passed only one arg, could be main or sub
    try:
        # * assume precise main topic, i.e. "git"
        return MAIN_TOPICS[main_topic]()
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
            return print_topic(topic)
        else:
            # * indeed a precise subtopic, call the main topic's fn and pass subtopic param
            try:
                return fn(f'_{topic.upper()}')
            except TypeError as duplicate_sub_topic:
                # * error: "'list' object is not callable". some topics share same subtopic. choose main topic
                fn: List[Callable[[str], Any]]
                
                # TODO (bugs): 
                #  (1) If an ALIAS of a subtopic is the same as a SUBTOPIC of another main topic,
                #  this is called (shouldn't). Aliases aren't subtopics. (uncomment asyncio # _SUBPROCESS = _SUBPROCESSES)
                #  (2) main topics with both @alias and @syntax decors, that have the issue above ("(1)"), raise
                #  a ValueError in igit prompt, because the same main topic function is passed here for each subtopic and subtopic alias.
                #  ValueError: ('NumOptions | __init__(opts) duplicate opts: ', ('<function asyncio at 0x7f5dab684ca0>', '<function asyncio at 0x7f5dab684ca0>', '<function python at 0x7f5dab669a60>'))
                idx, choice = prompt.choose(f"'{topic}' exists in several topics, which one did you mean?",
                                            # *map(str, map(draw_out_decorated_fn, fn)))
                                            *map(str, fn))
                return fn[idx](f'_{topic.upper()}')


# todo: custom help string that describes --check (perform_checks)  https://click.palletsprojects.com/en/7.x/documentation/#help-parameter-customization
@click.command()
@click.argument('main_topic')
@click.argument('sub_topic', required=False)
@unrequired_opt('-l', '--list', 'list_subtopics', is_flag=True, help='list sub topics')
@unrequired_opt('-e', '--edit', 'edit', is_flag=True, help='edit MAIN_TOPIC')
def main(main_topic, sub_topic, list_subtopics, edit):
    loggr = logger()
    loggr.title(main_topic, sub_topic, list_subtopics, edit, varnames=True)
    if list_subtopics:
        brightprint(main_topic + '\n', 'bold', 'ul')
        [brightprint('  ' + st) for st in sorted(MAIN_TOPICS[main_topic].sub_topics)]
        return
    if edit:
        import os
        manualsfile = os.path.join(os.path.dirname(__file__), 'manuals.py')
        os.system(f'pycharm "{manualsfile}"')
        return
    
    print_topic(main_topic, sub_topic)
