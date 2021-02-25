import inspect
import sys
from abc import abstractmethod
from enum import Enum
from typing import TypeVar, Dict, Generator, Tuple, Any, Type, NoReturn

# from igit_debug.loggr import Loggr
from more_termcolor import colors

# from igit.abcs import prettyrepr
# from rich.console import Console
# from igit.util.misc import darkprint
from regexp import YES_OR_NO
import logging
T = TypeVar('T')
# from rich.console import Console
#
# console = Console()
# logger = Loggr(__name__)


# noinspection PyUnresolvedReferences
def mutate_identifier(identifier: str):
    upper = identifier.upper()
    identifier = upper
    logging.debug(f'mutate_identifier({repr(identifier)}) yielding upper: {repr(upper)}')
    yield upper
    words = self.val.split(' ')
    if len(words) == 1:
        raise NotImplementedError(f"no word separators, and both lowercase and uppercase identifier is taken ('{upper.lower()}')")
    words_identifiers = ''.join(map(lambda s: s[0], words))
    identifier = words_identifiers
    logging.debug(f'mutate_identifier() yielding words_identifiers: {repr(words_identifiers)}')
    yield words_identifiers
    for i in range(len(words_identifiers)):
        new_identifiers = words_identifiers[:i] + words_identifiers[i].upper() + words_identifiers[i + 1:]
        identifier = new_identifiers
        logging.debug(f'mutate_identifier() yielding new_identifiers (#{i}): {repr(new_identifiers)}')
        yield new_identifiers
    raise StopIteration(f'mutate_identifier() exhausted all options: {repr(self)}')


class Flow(Enum):
    """
    >>> flow = Flow('continue')
    <Flow.CONTINUE: 'continue'>
    >>> flow == Flow.CONTINUE == Flow(Flow.CONTINUE)
    True
    """
    CONTINUE = 'continue'
    DEBUG = 'debug'
    QUIT = 'quit'
    
    @staticmethod
    def laxinit(value) -> 'Flow':
        """Case insensitive"""
        if isinstance(value, str):
            return Flow(value.lower())
        return Flow(value)


# @prettyrepr
class Item:
    identifier: str
    value: Any
    
    def __init__(self) -> None:
        super().__init__()
        self._identifier = None
        self._value = None
    
    def __hash__(self) -> int:
        return hash((self.value, self.identifier))
    
    def __eq__(self, o: object) -> bool:
        if isinstance(o, (Item, Flow, str)):
            # both Item and Flow have a 'value' property
            return self.value == o
        
        return super().__eq__(o)
    
    def __str__(self):
        valuestr = str(self.value)
        if len(valuestr) >= 80:
            return valuestr[:77] + '...'
        return valuestr
    
    # def __repr__(self):  # uncomment if has prepr() fn (originally from @prettyrepr)
    #     identifier = f'[{self._identifier}]'
    #     return f"""{self.prepr()}({repr(str(self))}) | {identifier}"""
    
    @property
    def identifier(self) -> str:
        return self._identifier
    
    @identifier.setter
    def identifier(self, identifier: str):
        self._identifier = identifier
    
    @property
    def value(self) -> str:
        return self._value
    
    @value.setter
    def value(self, value: str):
        self._value = value


class MutableItem(Item):
    is_yes_or_no: bool
    
    def __init__(self, value, identifier=None) -> None:
        super().__init__()
        self.identifier = identifier
        self.value: str = value
    
    def __repr__(self):
        superrepr = repr(super())
        if bool(YES_OR_NO.fullmatch(self.identifier)):
            superrepr += f', is_yes_or_no: {True}'
        return superrepr
    
    def __hash__(self) -> int:
        return hash((self.value, self.identifier, self.is_yes_or_no))
    
    @property
    def is_yes_or_no(self):
        ret = bool(YES_OR_NO.fullmatch(self.identifier))
        # darkprint(f'{repr(self)}.is_yes_or_no() → {ret}')
        return ret
        # return self._is_yes_or_no
    
    # @property
    # def value(self):
    #     return self._value
    #
    # @value.setter
    # def value(self, value: str):
    #     # TODO: this is buggy, because:
    #     #  1. prompt.answer is bool if KEY.lower() == 'y', not val
    #     #  2. y='something' should register as yes or no, but doesn't
    #     self._value = value
    #     self._is_yes_or_no = bool(YES_OR_NO.fullmatch(value))


class LexicItem(MutableItem):
    def mutate_identifier(self):
        upper = self.identifier.upper()
        self.identifier = upper
        # darkprint(f'{repr(self)} | mutate_identifier() yielding upper: {repr(upper)}')
        yield upper
        words = self.value.split(' ')
        if len(words) == 1:
            raise NotImplementedError(f"no word separators, and both lowercase and uppercase identifier is taken ('{upper.lower()}')")
        words_identifiers = ''.join(map(lambda s: s[0], words))
        self.identifier = words_identifiers
        # darkprint(f'mutate_identifier() yielding words_identifiers: {repr(words_identifiers)}')
        yield words_identifiers
        for i in range(len(words_identifiers)):
            new_identifiers = words_identifiers[:i] + words_identifiers[i].upper() + words_identifiers[i + 1:]
            self.identifier = new_identifiers
            # darkprint(f'mutate_identifier() yielding new_identifiers (#{i}): {repr(new_identifiers)}')
            yield new_identifiers
        raise StopIteration(f'mutate_identifier() exhausted all options: {repr(self)}')


class FlowItem(Item):
    value: Flow
    
    def __init__(self, value) -> None:
        super().__init__()
        flow = Flow.laxinit(value)
        self._identifier = flow.value
        self._value = flow
    
    def __hash__(self) -> int:
        return hash((self.value, self.identifier))
    
    # def __repr__(self):  # uncomment if has prepr() fn (originally from @prettyrepr)
    #     # TODO: why is it not working with repr(super())?
    #     identifier = f'[{self._identifier}]'
    #     return f"""{self.prepr()}({repr(str(self))}) | {identifier}"""
    
    # def __init__(self, value):
    #     flow = Flow(value)
    #     self.identifier = flow.value
    #     self.value = flow.name
    
    # @classmethod
    # def full_names(cls) -> set:
    #     """→ {'continue', 'debug', 'quit'}"""
    #     return set(map(str.lower, FlowItem._member_names_))
    
    # @classmethod
    # def from_full_name(cls, fullname: str) -> 'FlowItem':
    #     """
    #     >>> FlowItem.from_full_name('continue')
    #     FlowItem.CONTINUE
    #     """
    #     try:
    #         return FlowItem._member_map_[str(fullname).upper()]
    #     except KeyError as e:
    #         raise ValueError(f"'{fullname}' is not a valid {cls.__qualname__}") from None
    
    @property
    def identifier(self):
        return self._identifier
    
    @identifier.setter
    def identifier(self, identifier):
        raise AttributeError(f"{repr(self)}.identifier({repr(identifier)}): Enum can't set self.identifier because self.value is readonly")
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, value):
        raise AttributeError(f"{repr(self)}.value({repr(value)}): Enum can't set self.value because self.value is readonly")
    
    @property
    def DEBUG(self):
        return self.value is Flow.DEBUG
    
    @property
    def CONTINUE(self):
        return self.value is Flow.CONTINUE
    
    @property
    def QUIT(self):
        return self.value is Flow.QUIT
    
    def execute(self) -> None:
        print(f'execute() self: ', self)
        if self.QUIT:
            sys.exit('Aborting')
        if self.CONTINUE:
            print(colors.italic('continuing'))
            return None
        if self.DEBUG:
            frame = inspect.currentframe()
            up_frames = []
            while frame.f_code.co_filename == __file__:
                frame = frame.f_back
                up_frames.append(frame.f_code.co_name)
            print(colors.bold(f'u {len(up_frames)}'), colors.dark(repr(up_frames)))
            breakpoint()
            
            return None
        raise NotImplementedError(f"don't support this enum type yet: {self}")


class Items(Dict[str, MutableItem]):
    _itemcls = MutableItem
    
    def __new__(cls: Type['Items'], *args: Any, **kwargs: Any) -> 'Items':
        # TODO: apply items_gen here (scratch_MyDict.py), so can init and behave like normal dict (KeywordItems())
        # darkprint(f'{cls.__qualname__}.__new__(*args, **kwargs): {args}, {kwargs}')
        return super().__new__(cls, *args, **kwargs)
    
    def __init__(self, items):
        super().__init__()
        # logger.debug('items:', items)
        for value, identifier in self.items_gen(items):
            item = self._itemcls(value, identifier)
            self.store(item)
            # logger.debug(f'\titem: {item}')
    
    def __repr__(self):
        string = '{\n\t'
        for identifier, item in self.items():
            string += f'{repr(identifier)}: {repr(item)}\n\t'
        return string + '}'
    
    @abstractmethod
    def items_gen(self, items) -> Generator[Tuple[str, str], None, None]:
        ...
    
    def store(self, item: MutableItem):
        if item.identifier in self:
            try:
                self.mutate_until_unique(item)
            except AttributeError as e:
                # no item.mutate_identifier(), probably a FlowItem
                # mutate stored item instead
                stored_item = self.get(item.identifier)
                self[item.identifier] = item
                self.mutate_until_unique(stored_item)
                self[stored_item.identifier] = stored_item
            else:
                # item mutated successfully
                self[item.identifier] = item
        else:
            self[item.identifier] = item
    
    @abstractmethod
    def mutate_until_unique(self, item: MutableItem):
        ...
    
    def __setitem__(self, k: str, v) -> None:
        if k in self:
            existing_item = self.get(k)
            self[k] = v
            self.mutate_until_unique(existing_item)
        super().__setitem__(k, v)


class KeywordItems(Items):
    def items_gen(self, kw_items: dict):
        for kw, value in kw_items.items():
            # kw is identifier
            yield value, kw
    
    def mutate_until_unique(self, item: MutableItem):
        raise NotImplementedError(f"{repr(self)}.mutate_until_unique(item={repr(item)}) not implemented")


class NumItems(Items):
    def items_gen(self, num_items):
        for idx, value in enumerate(num_items):
            # idx is identifier
            yield value, str(idx)
    
    def mutate_until_unique(self, item: MutableItem) -> MutableItem:
        """Identifiers are sorted digits. Tries to fill a gap if exists, otherwise just appends to the list"""
        identifiers = sorted(map(int, self.keys()))
        for idx, identifier in enumerate(identifiers[:-1]):
            plus1 = identifier + 1
            if identifiers[idx + 1] > plus1:
                # there's a gap, e.g. [1, 2, 4, 5]
                item.identifier = str(plus1)
                break
        else:
            # reached end of loop with no holes
            item.identifier = str(identifiers[-1] + 1)
        return item


class LexicItems(Items):
    _itemcls = LexicItem
    
    def items_gen(self, lexic_items):
        for value in lexic_items:
            # initial is identifier
            yield value, value[0]
    
    def mutate_until_unique(self, item: LexicItem) -> NoReturn:
        try:
            for mutation in item.mutate_identifier():
                if mutation in self:
                    continue
                return
        except AttributeError as e:
            raise NotImplementedError
    # no item.mutate_identifier, probably a FlowItem
