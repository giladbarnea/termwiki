#!/usr/bin/env python3.8
"""
get_main_topics() is called to popuplate MAIN_TOPICS.
"""
import inspect
import logging
import re
import sys
# from functools import wraps
from collections import defaultdict
from typing import Callable, Collection

import click

# import search
# import prompt
from manuals.common.click_extension import unrequired_opt
# brightprint = lambda s, *colors: cprint(s, 'bright white', *colors)
from manuals.common.types import ManFn
# from more_termcolor import cprint
from manuals.formatting import h2

SUB_TOPIC_RE = re.compile(r'_[A-Z0-9_]*\s*=\s*(rf|fr|f)["\']{3}')


def get_unused_subtopics(undecorated_main_topic_fn) -> list[str]:
    """python -m manuals --doctor calls this"""
    # TODO (bug): Doesn't check if __LOGGING_FORMATTER in _LOGGING
    # TODO (bug): If _MANAGE = _MANAGEPY = f"""... and _MANAGEPY in last block, says _MANAGE is unused
    lines = inspect.getsource(undecorated_main_topic_fn).splitlines()
    try:
        last_block_linenum = -next(i for i, line in enumerate(reversed(lines)) if line.strip() == 'else:') - 1
    except StopIteration:
        # no else: clause, just `return """...`
        last_block_linenum = -next(i for i, line in enumerate(reversed(lines)) if line.strip().startswith('return')) - 1
    lines_before_last_block = {line.strip().partition('=')[0].strip() for line in lines[:last_block_linenum] if
                               line and SUB_TOPIC_RE.search(line) and '__' not in line}
    line_inside_last_block = {line.strip()[1:-1] for line in lines[last_block_linenum:] if
                              (stripped := line.strip()).startswith('{_') and stripped.endswith('}')}
    if lines_missing_inside_last_block := lines_before_last_block - line_inside_last_block:
        return sorted(list(lines_missing_inside_last_block))


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
        manual: ManFn = getattr(manuals, main_topic)
        if not inspect.isfunction(manual):
            continue
        
        if main_topic.endswith('_'):  # inspect_()
            name = main_topic[:-1]
        else:
            name = main_topic
        
        ## dont draw_out_wrapped_fn because then syntax() isn't called
        main_topics[name] = manual
        if alias := getattr(manual, 'alias', None):
            main_topics[alias] = manual
    
    return main_topics


MAIN_TOPICS: dict[str, ManFn] = populate_main_topics()


def get_sub_topic_var_names(fn: ManFn) -> list[str]:
    return [n for n in fn.__code__.co_varnames if n.isupper()]


TSubTopics = dict[str, set[ManFn]]


def populate_sub_topics(*, print_unused_subtopics=False) -> TSubTopics:
    """Sets bash.sub_topics = [ "cut" , "for" ] for each MAIN_TOPICS.
    Removes (d)underscore and lowers _CUT and __FOR.
    Returns e.g. `{ 'cut' : bash , 'args' : [ bash , pdb ] }`"""
    all_sub_topics: TSubTopics = defaultdict(set)
    for name, main_topic in MAIN_TOPICS.items():
        
        # sub_topic_var_names = [n for n in draw_out_decorated_fn(main_topic_fn).__code__.co_varnames if n.isupper()]
        # draw_out_decorated_fn is necessary because MAIN_TOPICS has to store the fns in the wrapped form (to call them later)
        setattr(main_topic, 'sub_topics', set())
        undecorated_main_topic_fn = draw_out_decorated_fn(main_topic)
        sub_topic_var_names = get_sub_topic_var_names(undecorated_main_topic_fn)
        if not sub_topic_var_names:
            continue
        
        if print_unused_subtopics:
            unused_subtopics = get_unused_subtopics(undecorated_main_topic_fn)
            if unused_subtopics:
                spaces = ' ' * (max(map(len, MAIN_TOPICS.keys())) - len(name))
                print(f"{name!r} doesn't print:{spaces}{', '.join(unused_subtopics)}")
        
        for sub_topic_var_name in sub_topic_var_names:
            ## DONT account for dunder __ARGUMENTS, it's being handled by get_sub_topic().
            #   If handled here, eventually bash('_ARGUMENTS') is called which errors.
            #   likewise: if f'_{sub_topic}' in manual.sub_topics:
            
            sub_topic_var_name = sub_topic_var_name.strip().lower()[1:]
            main_topic.sub_topics.add(sub_topic_var_name)
            all_sub_topics[sub_topic_var_name].add(main_topic)
    
    return all_sub_topics


SUB_TOPICS: TSubTopics = populate_sub_topics()


def fuzzy_find_topic(topic: str,
                     collection: Collection,
                     *extra_opts,
                     raise_if_exhausted=False,
                     **extra_kw_opts) -> tuple:
    """If user continue'd through the whole collection, raises KeyError if `raise_if_exhausted` is True. Otherwise, returns None"""
    # not even a subtopic, could be gibberish
    # try assuming it's a substring
    from manuals import search, prompt
    for maybes, is_last in search.iter_maybes(topic, collection, criterion='substring'):
        if not maybes:
            continue
        
        kwargs = dict(Ep='Edit manuals.py with pycharm',
                      Ec='Edit manuals.py with vscode',
                      Em='Edit manuals.py with micro')
        
        if is_last and raise_if_exhausted:
            kwargs.update(flowopts='quit')
        else:
            kwargs.update(flowopts='quit', no='continue')
        # TODO: if a match is a subtopic, present maintopic.subtopic in choose
        key, choice = prompt.choose(f"Did you mean any of these?",
                                    *extra_opts,
                                    *maybes,
                                    **kwargs,
                                    **extra_kw_opts)
        if choice == prompt.Flow.CONTINUE:
            continue
        if isinstance(key, str) and key.startswith('E'):
            import os
            if key == 'Ep':
                status = os.system(f'pycharm "{__file__}"')
            elif key == 'Ec':
                status = os.system(f'code "{__file__}"')
            elif key == 'Em':
                status = os.system(f'micro "{__file__}"')
            sys.exit(status)
        return key, choice.value
    if raise_if_exhausted:
        raise KeyError(f"{topic = !r} isn't in collection")
    return None, None


def get_sub_topic(main_topic: str, sub_topic: str) -> str:
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
    logging.debug(f"get_sub_topic({main_topic = !r}, {sub_topic = !r})")
    if main_topic not in MAIN_TOPICS:
        print(f"[info] Unknown main topic: {main_topic!r}. Fuzzy finding among MAIN_TOPICS...")
        main_topic = fuzzy_find_topic(main_topic, MAIN_TOPICS, raise_if_exhausted=True)
    
    manual: ManFn = MAIN_TOPICS[main_topic]
    if sub_topic in manual.sub_topics:
        return manual(f'_{sub_topic.upper()}')
    
    if f'_{sub_topic}' in manual.sub_topics:
        # mm bash syntax → manual.sub_topics has '_syntax' → pass '__SYNTAX'
        return manual(f'__{sub_topic.upper()}')
    
    try:
        # sometimes functions have alias logic under 'if subject:' clause, for example bash
        # has 'subject.startswith('<')'. so maybe sub_topic works
        return manual(sub_topic)
    except KeyError:
        print((f"[info] sub topic '{sub_topic}' isn't a sub topic of '{main_topic}'. "
               f"Searching among '{main_topic}'s sub topics..."))
        key, chosen_sub_topic = fuzzy_find_topic(sub_topic,
                                                 manual.sub_topics,
                                                 raise_if_exhausted=False,
                                                 # keep uppercase P so doesn't collide with topics
                                                 P=f"print '{main_topic}' w/o subtopic")
        if key == 'P':
            return manual()
        
        if chosen_sub_topic is not None:
            return manual(f'_{chosen_sub_topic.upper()}')
        
        if sub_topic in SUB_TOPICS:
            print(f"[info] '{sub_topic}' isn't a sub topic of '{main_topic}', but it belongs to these topics:")
            return print_manual(sub_topic)
        
        print(f"[info] '{sub_topic}' doesn't belong to any topic. Searching among all SUB_TOPICS...")
        key, sub_topic = fuzzy_find_topic(sub_topic,
                                          SUB_TOPICS,
                                          raise_if_exhausted=True,
                                          P=f"print '{main_topic}' w/o subtopic")
        if key == 'P':
            return manual()
        
        return manual(f'_{sub_topic.upper()}')


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
    
    # ** Passed only one arg; could be main or sub. Maybe main?
    if topic in MAIN_TOPICS:
        return print(MAIN_TOPICS[topic]())
    
    # ** Not a main topic. Maybe it's a precise sub topic, i.e. "diff"
    sub_topic_key = None
    if topic in SUB_TOPICS:
        sub_topic_key = topic
    else:
        for sub_topic in SUB_TOPICS:
            sub_topic_no_leading_underscore = sub_topic.removeprefix('_')
            if topic == sub_topic_no_leading_underscore:
                sub_topic_key = sub_topic
                break
    if sub_topic_key:
        # * Indeed a precise subtopic
        ## Maybe multiple manuals have it
        if len(SUB_TOPICS[sub_topic_key]) > 1:
            from manuals import prompt
            manuals: list[ManFn] = list(SUB_TOPICS[sub_topic_key])  # for index
            
            # TODO (bugs):
            #  (1) If an ALIAS of a subtopic is the same as a SUBTOPIC of another main topic,
            #    this is called (shouldn't). Aliases aren't subtopics. (uncomment asyncio # _SUBPROCESS = _SUBPROCESSES)
            #  (2) main topics with both @alias and @syntax decors, that have the issue above ("(1)"), raise
            #    a ValueError in igit prompt, because the same main topic function is passed here for each subtopic and subtopic alias.
            #  ValueError: ('NumOptions | __init__(opts) duplicate opts: ', ('<function asyncio at 0x7f5dab684ca0>', '<function asyncio at 0x7f5dab684ca0>', '<function python at 0x7f5dab669a60>'))
            idx, choice = prompt.choose(f"{sub_topic_key!r} exists in several topics, which one did you mean?",
                                        *[man.__qualname__ for man in manuals],
                                        flowopts='quit'
                                        )
            return print(manuals[idx](f'_{sub_topic_key.upper()}'))
        
        ## Unique subtopic
        manual, *_ = SUB_TOPICS[sub_topic_key]
        return print(manual(f'_{sub_topic_key.upper()}'))
    
    # ** Not a precise subtopic. find something precise, either a main or sub topic
    key, topic = fuzzy_find_topic(topic,
                                  set(MAIN_TOPICS.keys()) | set(SUB_TOPICS.keys()),
                                  raise_if_exhausted=True)
    return print_manual(topic)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('main_topic', required=False)
@click.argument('sub_topic', required=False)
@unrequired_opt('-l', '--list', 'list_topics_or_subtopics', is_flag=True, help="List main topic's sub topics if MAIN_TOPIC is provided, else list all main topics")
@unrequired_opt('--doctor', 'print_unused_subtopics', is_flag=True, help="Print any subtopics that are skipped erroneously in a main topic's else clause")
def get_topic(main_topic, sub_topic, list_topics_or_subtopics, print_unused_subtopics):
    logging.debug(f'manuals.get_topic({main_topic = }, {sub_topic = }, {list_topics_or_subtopics = })')
    if print_unused_subtopics:
        populate_sub_topics(print_unused_subtopics=True)
        return
    if list_topics_or_subtopics:
        if main_topic:
            print(f"{h2(main_topic)}")
            [print(f' · {sub}') for sub in sorted(MAIN_TOPICS[main_topic].sub_topics)]
        else:
            for main_name, main_function in sorted(MAIN_TOPICS.items()):
                alias = getattr(main_function, 'alias', None)
                if alias and alias == main_name:
                    continue
                title = f"\n{h2(main_name)}"
                if alias:
                    title += f" ({main_function.alias})"
                print(title)
                [print(f' · {sub}') for sub in sorted(MAIN_TOPICS[main_name].sub_topics)]
        return
    
    print_manual(main_topic, sub_topic)
