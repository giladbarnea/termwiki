#!/usr/bin/env python3.8
"""
get_main_topics() is called to popuplate MAIN_TOPICS.
"""
import inspect
import logging
import re
import sys
# from functools import wraps
from typing import Callable, Union, Any, Collection

import click

# import search
# import prompt
from manuals.common.click_extension import unrequired_opt
# brightprint = lambda s, *colors: cprint(s, 'bright white', *colors)
from manuals.common.types import ManFn
# from more_termcolor import cprint
from manuals.formatting import h2

SUB_TOPIC_RE = re.compile(r'_[A-Z]*\s?=\s?(rf|fr|f)"""')


def get_unused_subtopics(undecorated_main_topic_fn):
    """python -m manuals <MAIN TOPIC> --doctor calls this"""
    lines = inspect.getsource(undecorated_main_topic_fn).splitlines()
    try:
        last_else_idx = -next(i for i, line in enumerate(reversed(lines)) if line.strip() == 'else:') - 1
    except StopIteration:
        # no else: clause, just return (like click)
        last_else_idx = -next(i for i, line in enumerate(reversed(lines)) if line.strip().startswith('return ')) - 1
    before_else = [line.strip().partition('=')[0].strip() for line in lines[:last_else_idx] if
                   line and SUB_TOPIC_RE.search(line) and not '__' in line]
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


def populate_main_topics() -> dict[str, ManFn]:
    """Populates a { 'pandas' : pandas , 'inspect' : inspect_, 'gh' : githubcli } dict from `manuals` module"""
    from . import manuals
    main_topics = dict()
    for main_topic in dir(manuals):
        if main_topic in manuals.EXCLUDE:
            continue
        fn: Callable = getattr(manuals, main_topic)
        if not inspect.isfunction(fn):
            continue
        
        if main_topic.endswith('_'):  # inspect_()
            name = main_topic[:-1]
        else:
            name = main_topic
        
        ## dont draw_out_wrapped_fn because then syntax() isn't called
        main_topics[name] = fn
        if alias := getattr(fn, 'alias', None):
            main_topics[alias] = fn
    
    return main_topics


MAIN_TOPICS: dict[str, ManFn] = populate_main_topics()


def get_sub_topic_var_names(fn: ManFn) -> list[str]:
    return [n for n in fn.__code__.co_varnames if n.isupper()]


TSubTopics = dict[str, Union[set[ManFn], ManFn]]


def populate_sub_topics(*, print_unused_subtopics=False) -> TSubTopics:
    """Sets bash.sub_topics = [ "cut" , "for" ] for each MAIN_TOPICS.
    Removes (d)underscore and lowers _CUT and __FOR.
    Returns e.g. `{ 'cut' : bash , 'args' : [ bash , pdb ] }`"""
    # var_reg = r'_[A-Z0-9_]*'
    # matches `_SUBTOPIC = fr"""..."""` and `_ST = _SUBTOPIC`
    # sub_topic_reg = re.compile(fr'\s*{var_reg}\s?=\s?(r?fr?""".*|{var_reg})\n')
    # subject_sig_re = re.compile(r'subject\s?=\s?None')
    
    all_sub_topics = dict()
    # for main_topic_fn in list(MAIN_TOPICS.values()):
    for name, main_topic in MAIN_TOPICS.items():
        
        # sub_topic_var_names = [n for n in draw_out_decorated_fn(main_topic_fn).__code__.co_varnames if n.isupper()]
        # draw_out_decorated_fn is necessary because MAIN_TOPICS has to store the fns in the wrapped form (to call them later)
        setattr(main_topic, 'sub_topics', set())
        undecorated_main_topic_fn = draw_out_decorated_fn(main_topic)
        sub_topic_var_names = get_sub_topic_var_names(undecorated_main_topic_fn)
        if not sub_topic_var_names:
            continue
        # lines, _ = inspect.getsourcelines(main_topic_fn)
        # if not re.search(subject_sig_re, lines[0]) and not re.search(subject_sig_re, lines[1]):
        # lines[1]: decorated functions' first line is the @decorator
        # if not 'subject' in inspect.getfullargspec(main_topic).args:
        #     continue
        
        # lines = [l.strip() for l in lines if re.fullmatch(sub_topic_reg, l)]
        # if not lines:  # has subject=None in sig but no actual sub topic vars
        #     continue
        
        if print_unused_subtopics:
            print(get_unused_subtopics(undecorated_main_topic_fn))
        
        for sub_topic_var_name in sub_topic_var_names:
            # DONT account for dunder __ARGUMENTS, it's being handled by get_sub_topic().
            # If handled here, eventually bash('_ARGUMENTS') is called which errors.
            
            ## Deprecated
            # if (stripped := sub_topic_var_name.strip()).startswith('__'):
            #     sub_topic_var_name = stripped.lower()[2:]
            # else:  # starts with single '_'
            #     sub_topic_var_name = stripped.lower()[1:]
            
            sub_topic_var_name = sub_topic_var_name.strip().lower()[1:]
            main_topic.sub_topics.add(sub_topic_var_name)
            if sub_topic_var_name in all_sub_topics:
                # this means duplicate subtopic, for different main topics
                # in that case, the value is set to be a list of subtopics
                if isinstance(all_sub_topics[sub_topic_var_name], set):
                    all_sub_topics[sub_topic_var_name].add(main_topic)
                else:
                    # create a new list
                    all_sub_topics[sub_topic_var_name] = {all_sub_topics[sub_topic_var_name], main_topic}
            else:
                # no duplicate sub topics; value is set to be simply the function
                all_sub_topics[sub_topic_var_name] = main_topic
    
    return all_sub_topics


SUB_TOPICS: TSubTopics = populate_sub_topics()


def fuzzy_find_topic(topic: str, collection: Collection, *extra_opts, raise_if_exhausted=False, **extra_kw_opts) -> tuple:
    """If user continue'd through the whole collection, raises KeyError if `raise_if_exhausted` is True. Otherwise, returns None"""
    # not even a subtopic, could be gibberish
    # try assuming it's a substring
    from manuals import search, prompt
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
        raise KeyError(f"{topic!r} isn't in collection")
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
    logging.debug(f"get_sub_topic({main_topic = }, {sub_topic = })")
    if main_topic not in MAIN_TOPICS:
        print(f"[info] Unknown main topic: '{main_topic}'. Searching among MAIN_TOPICS...[/]")
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
        print((f"[info] sub topic '{sub_topic}' isn't a sub topic of '{main_topic}'. "
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
            print(f"[info] '{sub_topic}' isn't a sub topic of '{main_topic}', but it belongs to these topics:[/]")
            return print_manual(sub_topic)
        
        print(f"[info] '{sub_topic}' doesn't belong to any topic. Searching among all SUB_TOPICS...[/]")
        key, sub_topic = fuzzy_find_topic(sub_topic,
                                          SUB_TOPICS,
                                          raise_if_exhausted=True,
                                          P=f"print '{main_topic}' w/o subtopic")
        if key == 'P':
            return main_topic_fn()
        
        return main_topic_fn(f'_{sub_topic.upper()}')


def print_manual(topic: str, sub_topic=None):
    """If passed correct topic(s), prints.
    If not correct, finds the correct with fuzzy search and calls itself."""
    logging.debug(f"print_manual({repr(topic)}, {repr(sub_topic)})")
    if sub_topic:
        # ** Passed both topic and sub_topic
        sub_topic_str = get_sub_topic(topic, sub_topic)
        # sub_topic_str = get_sub_topic(topic, sub_topic) \
        #     .replace('[h1]', '[bold underline reverse bright_white]') \
        #     .replace('[h2]', '[bold underline bright_white]') \
        #     .replace('[h3]', '[bold bright_white]') \
        #     .replace('[h4]', '[info]') \
        #     .replace('[h5]', '[white]') \
        #     .replace('[c]', '[dim]')
        # return console.print(sub_topic_str)
        return print(sub_topic_str)
    
    # ** Passed only one arg; could be main or sub
    if topic in MAIN_TOPICS:
        return print(MAIN_TOPICS[topic]())
    
    # ** Maybe it's a precise sub topic, i.e. "diff"
    if topic in SUB_TOPICS:
        # * Indeed a precise subtopic
        ## Maybe multiple manuals have it
        if isinstance(SUB_TOPICS[topic], set):
            import prompt
            manuals: list[ManFn] = list(SUB_TOPICS[topic]) # for index
    
            # TODO (bugs):
            #  (1) If an ALIAS of a subtopic is the same as a SUBTOPIC of another main topic,
            #    this is called (shouldn't). Aliases aren't subtopics. (uncomment asyncio # _SUBPROCESS = _SUBPROCESSES)
            #  (2) main topics with both @alias and @syntax decors, that have the issue above ("(1)"), raise
            #    a ValueError in igit prompt, because the same main topic function is passed here for each subtopic and subtopic alias.
            #  ValueError: ('NumOptions | __init__(opts) duplicate opts: ', ('<function asyncio at 0x7f5dab684ca0>', '<function asyncio at 0x7f5dab684ca0>', '<function python at 0x7f5dab669a60>'))
            idx, choice = prompt.choose(f"{topic!r} exists in several topics, which one did you mean?",
                                        *[man.__qualname__ for man in manuals],
                                        flowopts='quit'
                                        )
            return print(manuals[idx](f'_{topic.upper()}'))
        
        ## Unique subtopic
        return print(SUB_TOPICS[topic](f'_{topic.upper()}'))
    
    # ** Not a precise subtopic. find something precise, either a main or sub topic
    key, topic = fuzzy_find_topic(topic,
                                  set(MAIN_TOPICS.keys()) | set(SUB_TOPICS.keys()),
                                  raise_if_exhausted=True)
    return print_manual(topic)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('main_topic')
@click.argument('sub_topic', required=False)
@unrequired_opt('-l', '--list', 'list_subtopics', is_flag=True, help='list sub topics')
@unrequired_opt('--doctor', 'print_unused_subtopics', is_flag=True, help="prints any subtopics that are skipped erroneously in a main topic's else clause")
def get_topic(main_topic, sub_topic, list_subtopics, print_unused_subtopics):
    logging.debug(f'myman.get_topic({main_topic = }, {sub_topic = }, {list_subtopics = })')
    if print_unused_subtopics:
        populate_sub_topics(print_unused_subtopics=True)
        return
    if list_subtopics:
        print(f"{h2(main_topic)}\n")
        [print(f'{st}') for st in sorted(MAIN_TOPICS[main_topic].sub_topics)]
        return
    
    print_manual(main_topic, sub_topic)
