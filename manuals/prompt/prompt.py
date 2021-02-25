from typing import Union, Tuple, overload

import logging
# from igit_debug.investigate import logonreturn, logreturn
from more_termcolor import colors

# from igit.abcs import prettyrepr
from .item import MutableItem, FlowItem, LexicItem
from .options import Options, NumOptions, LexicOptions
from . import util
# from igit.util.misc import darkprint, brightyellowprint


def _input(s):
    return util.clean(input(colors.brightwhite(s)))


# (str, str) or (str, FlowItem)
AnswerTuple = Union[Tuple[str, MutableItem], Tuple[str, FlowItem], Tuple[str, LexicItem]]
Answer = Union[AnswerTuple, bool]


# @prettyrepr
class BasePrompt:
    # bool or (str, MutableItem)
    answer: Answer
    options: Options
    
    # @logonreturn('self.answer', types=True)
    def __init__(self, question: str, **kwargs):
        # noinspection PyTypeChecker
        self.answer: Answer = None
        if 'flowopts' in kwargs:
            self.options.set_flow_opts(kwargs.pop('flowopts'))
        try:
            free_input = kwargs.pop('free_input')
        except KeyError:
            free_input = False
        
        # *  keyword-choices
        self.options.set_kw_options(**kwargs)
        
        # *  Complex Prompt
        dialog_string = self.dialog_string(question, free_input=free_input)
        # question = self.dialog_string(question, options, free_input=free_input)
        key, answer = self.get_answer(dialog_string, free_input=free_input)
        # darkprint(f'{repr(self)} | key: {repr(key)}, answer: {repr(answer)}')
        # *  FlowItem Answer
        if isinstance(answer, FlowItem):
            # flow_answer: FlowItem = FlowItem(answer)
            answer.execute()
            
            if answer.DEBUG:
                # debugger had already started and had finished in answer.execute() (user 'continue'd here)
                self.answer = self.get_answer(dialog_string)
            elif answer.CONTINUE:
                self.answer: Tuple[str, FlowItem] = key, answer
            else:
                raise NotImplementedError
        else:
            # *  DIDN'T answer any flow
            
            if isinstance(answer, MutableItem) and answer.is_yes_or_no:
                # darkprint(f'{repr(self)} no flow chosen, answer is yes / no. key: {repr(key)}, answer: {repr(answer)}, options: {self.options}')
                self.answer: bool = key.lower() in ('y', 'yes')
            else:
                # darkprint(f'{repr(self)} no flow chosen, answer is not yes / no. key: {repr(key)}, answer: {repr(answer)}, options: {self.options}')
                self.answer: Tuple[str, MutableItem] = key, answer
    
    # def __repr__(self) -> str:  # uncomment if has prepr() fn (originally from @prettyrepr)
    #     return f'{self.prepr()}(answer={repr(self.answer)}, options={repr(self.options)})'
    
    def dialog_string(self, question: str, *, free_input: bool) -> str:
        strings = []
        for optkey, optval in self.options.items.items():
            strings.append(f'[{optkey}]: {optval}')
        options_str = '\n\t'.join(strings)
        question_str = f'{question}'
        # if free_input:
        #     question_str += ' (free input allowed)'
        if options_str:
            dialog_string = f'{question_str}\n\t{options_str}\n\t'
        else:
            dialog_string = question_str + '\n\t'
        if free_input:
            dialog_string += '(free input allowed)\n\t'
        return dialog_string
    
    @overload
    def get_answer(self, dialog_string: str, *, free_input=False) -> Tuple[str, Union[MutableItem, LexicItem, FlowItem]]:
        ...
    
    @overload
    def get_answer(self, dialog_string: str, *, free_input=True) -> Tuple[None, str]:
        """`free_input = True`"""
        ...
    
    # @logreturn
    def get_answer(self, dialog_string: str, *, free_input=False):
        ans_key = _input(dialog_string)
        items = self.options.items
        if ans_key not in items:
            if ans_key and free_input:
                # * Free input
                return None, ans_key
            else:
                # TODO: this doesnt account for free_input = True, but no ans_key ('')
                while ans_key not in items:
                    logging.warning(f"Unknown option: '{ans_key}'")
                    ans_key = _input(dialog_string)
        ans_value = items[ans_key]
        # this is commented out because BasePrompt init needs to check if answer.is_yes_or_no
        # if hasattr(ans_value, 'value'):
        #     ans_value = ans_value.value
        
        return ans_key, ans_value


class LexicPrompt(BasePrompt):
    options: LexicOptions
    answer: Tuple[str, LexicItem]
    
    def __init__(self, prompt: str, *options: str, **kwargs):
        self.options = LexicOptions(*options)
        super().__init__(prompt, **kwargs)


class Confirmation(LexicPrompt):
    options: LexicOptions
    answer: bool
    
    def __init__(self, prompt: str, *options: str, **kwargs):
        if 'free_input' in kwargs:
            raise ValueError(f"Confirmation cannot have free input. kwargs: {kwargs}")
        super().__init__(prompt, *options, **kwargs)


class Action(BasePrompt):
    options: LexicOptions
    answer: Tuple[str, LexicItem]
    
    def __init__(self, question: str, *actions: str, **kwargs):
        if not actions:
            raise ValueError(f'At least one action is required')
        self.options = LexicOptions(*actions)
        if self.options.any_item(lambda item: item.is_yes_or_no):
            raise ValueError(f"Actions cannot include a 'yes' or 'no'. Received: {repr(actions)}")
        super().__init__(question, **kwargs)


# TODO: Choice can return index! change docs
class Choice(BasePrompt):
    """If `free_input=True`, `answer` may be (None, str) or (None, slice) (if input is e.g. "2:5").
    
    Otherwise, if a numeric choice is made, `answer` is (slice, MutableItem).
    
    If a lexic choice is made, `answer` is (key: str, LexicItem)."""
    options: NumOptions
    answer: Union[Tuple[slice, MutableItem], Tuple[str, LexicItem], Tuple[None, str], Tuple[None, slice]]
    
    def get_answer(self, question: str, *, free_input=False) -> Tuple[Union[None, str, slice], Union[MutableItem, LexicItem, str, slice]]:
        ans_key, ans_value = super().get_answer(question, free_input=free_input)
        if ans_key is None:
            # free input
            indexer = util.to_int_or_slice(ans_value)
            if indexer is not None:
                ans_value = indexer
        else:
            indexer = util.to_int_or_slice(ans_key)
            if indexer is not None:
                ans_key = indexer
        return ans_key, ans_value
    
    def __init__(self, question: str, *options: str, **kwargs):
        if not options:
            raise ValueError(f'At least one option is required when using Choice (contrary to Prompt)')
        self.options = NumOptions(*options)
        super().__init__(question, **kwargs)


def generic(prompt: str, *options: str, **kwargs: Union[str, tuple, bool]):
    """Most permissive, a simple wrapper for LexicPrompt. `options` are optional, `kwargs` are optional.
    Examples::

        generic('This and that, continue?', 'yes', flowopts='quit', free_input=True) → [y], [q] (free input allowed)
    """
    
    return LexicPrompt(prompt, *options, **kwargs).answer


@overload
def choose(prompt, *options: str, **kwargs: Union[str, tuple, bool]) -> Tuple[None, slice]:
    """`free_input = True` and user input was e.g. "2:5" thus converted successfully to slice."""
    ...


@overload
def choose(prompt, *options: str, **kwargs: Union[str, tuple, bool]) -> Tuple[None, str]:
    """`free_input = True` and user input was some string."""
    ...


@overload
def choose(prompt, *options: str, **kwargs: Union[str, tuple, bool]) -> Tuple[slice, MutableItem]:
    """User chose a numeric selection that was converted to slice."""
    ...


@overload
def choose(prompt, *options: str, **kwargs: Union[str, tuple, bool]) -> Tuple[str, LexicItem]:
    """User chose a lexic selection."""
    ...


def choose(prompt, *options: str, **kwargs: Union[str, tuple, bool]):
    """Presents `options` by *index*. Expects at least one option.
    
    If `free_input=True`, return type may be (None, str) or (None, slice) (if input is e.g. "2:5").
    
    Otherwise, if a numeric choice is made, return type is (idx: int, MutableItem).
    
    If a lexic choice is made, return type is (key: str, LexicItem).
    """
    
    answer = Choice(prompt, *options, **kwargs).answer
    return answer


# TODO: implement prompt.confirm('yes', 'quit', no='open with current') that returns bool (see search.py _choose_from_many())
def confirm(prompt, **kwargs: Union[str, tuple, bool]) -> bool:
    """A 'y/n' prompt.

    If `options` contains any "special options", they are presented by key.
    Examples::

        confirm('ice cream?', flowopts='quit') → [y], [n], [q]
        confirm('pizza?', flowopts=True) → [y], [n], [c], [d], [q]
        confirm('burger?', flowopts=('quit', 'debug')) → [y], [n], [q], [d]
        confirm('proceed?') → [y], [n]
    """
    
    return Confirmation(prompt, 'yes', 'no', **kwargs).answer


def action(question, *actions, **kwargs: Union[str, tuple, bool]) -> Tuple[str, LexicItem]:
    """Presents `options` by *key*.
    Compared to `confirm()`, `action()` can't be used to prompt for yes/no but instead prompts for strings.
    Example::

        action('uncommitted changes', 'stash & apply', flowopts = True)

    :param actions: must not be empty, and cannot contain 'yes' or 'no'.
    :param special_opts:
        If True, special options: ('continue', 'debug', 'quit') are also presented.
        If a str, it has to be one of the special options above.
        If tuple, has to contain only special options above.
    """
    
    return Action(question, *actions, **kwargs).answer
