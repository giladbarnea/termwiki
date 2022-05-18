#!/usr/bin/env python3.8
"""
get_main_topics() is called to popuplate MAIN_TOPICS.
"""
from __future__ import annotations

import inspect
import itertools as it
import logging
import sys
from collections import defaultdict
from typing import Callable, Collection

import click

from termwiki.colors import h2
from termwiki.common.click_extension import unrequired_opt
from termwiki.common.types import ManFn
from termwiki.consts import SUB_TOPIC_RE


def get_unused_subtopics(undecorated_main_topic_fn) -> list[str]:
    """python -m termwiki --doctor calls this"""
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
    # todo: use inspect.unwrap(), or fn.__wrapped__
    closure: tuple = fn.__closure__
    if not closure:
        # non-decorated functions' closure is None
        return fn
    return closure[-1].cell_contents


def populate_main_topics() -> dict[str, ManFn]:
    """Populates a { 'pandas' : pandas , 'inspect' : inspect_, 'gh' : githubcli } dict from `termwiki` module"""
    from termwiki.pages import pages
    from ._man import pages as private_manuals
    def iter_module_manuals(module):
        for _main_topic in dir(module):
            if _main_topic in module.EXCLUDE:
                continue
            _manual: ManFn = getattr(module, _main_topic)
            if not inspect.isfunction(_manual):
                continue
            if _main_topic.endswith('_'):  # inspect_()
                _name = _main_topic[:-1]
            else:
                _name = _main_topic
            yield _name, _manual

    main_topics = dict()
    for name, manual in it.chain(iter_module_manuals(pages),
                                 iter_module_manuals(private_manuals)):
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
    from termwiki import search, prompt
    for maybes, is_last in search.iter_maybes(topic, collection, criterion='substring'):
        if not maybes:
            continue

        kwargs = dict(Ep='Edit pages.py with pycharm',
                      Ec='Edit pages.py with vscode',
                      Em='Edit pages.py with micro')

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
    Function is called if both main_topic and sub_topic are specified.
    MAIN EXISTS?
     |      \
    yes     no
     |       \
     |      [find main]
     |        |     \
     |      found   nope
     |       /        \
     |     /        KeyError
     |   /
    SUB IN MAIN's SUBS?
     |          \
    yes         no
     |           \
    [return]    [find sub in main's]
                   |         \
                found       nope
                  |           \
                [return]    SUB IN ANY OTHER MAIN's SUBS?
                              |         \
                            yes         no
                             |           \
                            [return]    [find sub]
                                          |       \
                                        found      nope
                                          |         \
                                        [return]   KeyError
    """
    logging.debug(f"get_sub_topic({main_topic = !r}, {sub_topic = !r})")
    if main_topic not in MAIN_TOPICS:
        print(f"[info] Unknown main topic: {main_topic!r}. Fuzzy finding among MAIN_TOPICS...")
        main_topic = fuzzy_find_topic(main_topic, MAIN_TOPICS, raise_if_exhausted=True)

    manual: ManFn = MAIN_TOPICS[main_topic]
    for sub_topic_variation in (sub_topic,
                                f'{sub_topic}s',
                                f'_{sub_topic}',
                                f'_{sub_topic}s'):
        ## This accounts for 2 cases:
        # 1. 'mm python descriptor', but correct is 'descriptors', so add 's'
        # 2. 'mm bash while' -> manual.sub_topics has '_while' -> pass '__WHILE'
        if sub_topic_variation in manual.sub_topics:
            return manual(f'_{sub_topic_variation.upper()}')

    try:
        # sometimes functions have alias logic under 'if subject:' clause, for example bash
        # has 'subject.startswith('<')'. so maybe sub_topic works
        return manual(sub_topic)
    except KeyError:
        print(f"[info] sub topic {sub_topic!r} isn't a sub topic of {main_topic!r}. "
              f"Searching among {main_topic!r}'s sub topics...")
        key, chosen_sub_topic = fuzzy_find_topic(sub_topic,
                                                 manual.sub_topics,
                                                 raise_if_exhausted=False,
                                                 # keep uppercase P so doesn't collide with topics
                                                 P=f"print {main_topic!r} w/o subtopic")
        if key == 'P':
            return manual()

        if chosen_sub_topic is not None:
            return manual(f'_{chosen_sub_topic.upper()}')

        if sub_topic in SUB_TOPICS:
            print(f"[info] {sub_topic!r} isn't a sub topic of {main_topic!r}, but it belongs to these topics:")
            return print_manual(sub_topic)

        print(f"[info] {sub_topic!r} doesn't belong to any topic. Searching among all SUB_TOPICS...")
        key, sub_topic = fuzzy_find_topic(sub_topic,
                                          SUB_TOPICS,
                                          raise_if_exhausted=True,
                                          P=f"print {main_topic!r} without subtopic")
        if key == 'P':
            return manual()

        return manual(f'_{sub_topic.upper()}')


def print_manual(main_topic: str, sub_topic=None):
    """If passed correct main_topic(s), prints.
    If not correct, finds the correct with fuzzy search and calls itself."""
    logging.debug(f"print_manual({main_topic!r}, {sub_topic!r})")
    if sub_topic:
        # ** Passed both main_topic and sub_topic
        sub_topic_str = get_sub_topic(main_topic, sub_topic)
        # sub_topic_str = get_sub_topic(main_topic, sub_topic) \
        #     .replace('[h1]', '[bold underline reverse bright_white]') \
        #     .replace('[h2]', '[bold underline bright_white]') \
        #     .replace('[h3]', '[bold bright_white]') \
        #     .replace('[h4]', '[info]') \
        #     .replace('[h5]', '[white]') \
        #     .replace('[c]', '[dim]')
        # return console.print(sub_topic_str)
        return print(sub_topic_str)

    # ** Passed only one arg; could be main or sub. Maybe main?
    if main_topic in MAIN_TOPICS:
        return print(MAIN_TOPICS[main_topic]())

    # ** Not a main main_topic. Maybe it's a precise sub main_topic, i.e. "diff"
    sub_topic_key = None
    if main_topic in SUB_TOPICS:
        sub_topic_key = main_topic
    else:
        for sub_topic in SUB_TOPICS:
            sub_topic_no_leading_underscore = sub_topic.removeprefix('_')
            if main_topic == sub_topic_no_leading_underscore:
                sub_topic_key = sub_topic
                break
    if sub_topic_key:
        # * Indeed a precise subtopic
        ## Maybe multiple pages have it
        if len(SUB_TOPICS[sub_topic_key]) > 1:
            from termwiki import prompt
            manuals: list[ManFn] = list(SUB_TOPICS[sub_topic_key])  # for index

            # TODO (bugs):
            #  (1) If an ALIAS of a subtopic is the same as a SUBTOPIC of another main main_topic,
            #    this is called (shouldn't). Aliases aren't subtopics. (uncomment asyncio # _SUBPROCESS = _SUBPROCESSES)
            #  (2) main topics with both @alias and @syntax decors, that have the issue above ("(1)"), raise
            #    a ValueError in igit prompt, because the same main main_topic function is passed here for each subtopic and subtopic alias.
            #  ValueError: ('NumOptions | __init__(opts) duplicate opts: ', ('<function asyncio at 0x7f5dab684ca0>', '<function asyncio at 0x7f5dab684ca0>', '<function python at 0x7f5dab669a60>'))
            idx, choice = prompt.choose(f"{sub_topic_key!r} exists in several topics, which one did you mean?",
                                        *[man.__qualname__ for man in manuals],
                                        flowopts='quit'
                                        )
            return print(manuals[idx](f'_{sub_topic_key.upper()}'))

        ## Unique subtopic
        manual, *_ = SUB_TOPICS[sub_topic_key]
        return print(manual(f'_{sub_topic_key.upper()}'))

    # ** Not a precise subtopic. find something precise, either a main or sub main_topic
    key, main_topic = fuzzy_find_topic(main_topic,
                                       set(MAIN_TOPICS.keys()) | set(SUB_TOPICS.keys()),
                                       raise_if_exhausted=True)
    return print_manual(main_topic)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('main_topic', required=False)
@click.argument('sub_topic', required=False)
@unrequired_opt('-l', '--list', 'list_topics_or_subtopics', is_flag=True, help="List main topic's sub topics if MAIN_TOPIC is provided, else list all main topics")
@unrequired_opt('--doctor', 'print_unused_subtopics', is_flag=True, help="Print any subtopics that are skipped erroneously in a main topic's else clause")
def get_topic(main_topic: str | None,
              sub_topic: str | None,
              list_topics_or_subtopics: bool = False,
              print_unused_subtopics: bool = False):
    logging.debug(f'termwiki.get_topic({main_topic = !r}, {sub_topic = !r}, {list_topics_or_subtopics = }, {print_unused_subtopics = })')
    if print_unused_subtopics:  # mm --doctor
        populate_sub_topics(print_unused_subtopics=True)
        return
    if list_topics_or_subtopics:  # mm [MAIN_TOPIC] -l, --list
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
    if not main_topic:
        print('Error: Must specify a topic.\n')
        ctx = get_topic.context_class(get_topic)
        print(get_topic.get_help(ctx))
        return

    # mm MAIN_TOPIC [SUB_TOPIC]
    print_manual(main_topic, sub_topic)
