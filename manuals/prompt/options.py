from abc import ABC
from typing import Union, NoReturn, Callable, Any, Iterable

from more_termcolor import colors

from .item import MutableItem, Items, Flow
from .item import NumItems, LexicItems, KeywordItems
from .util import has_duplicates
# from .util.misc import darkprint
from .item import FlowItem
from err import DevError


# @prettyrepr
class Options(ABC):
    items: Items
    _itemscls = None
    
    # flowopts: Tuple['FlowItem', ...]
    
    def __init__(self, *opts: str):
        if has_duplicates(opts):
            raise ValueError(f"{repr(self)} | __init__(opts) duplicate opts: ", opts)
        self.items = self._itemscls(opts)
        # self.flowopts = tuple()
        # self._values = None
        # self._items = None
        # self._indexeditems = None
        # self._all_yes_or_no = None  # calculated only when None (not True or False)
    
    def __bool__(self):
        # return bool(self.items) or bool(self.flowopts)
        return bool(self.items)
    
    # def __repr__(self): # uncomment if has prepr() fn (originally from @prettyrepr)
    #     return f'{self.prepr()}(items = {repr(self.items)})'
    
    def set_flow_opts(self, flowopts: Union[str, Iterable, bool]) -> NoReturn:
        """Sets `self.flowopts` with FlowItem objects.
        Handles passing different types of flowopts (single string, tuple of strings, or boolean), and returns a FlowItem tuple."""
        # darkprint(f'{self.__class__.__qualname__}.set_flow_opts(flowopts={repr(flowopts)})')
        if flowopts is True:
            flowitems = tuple(map(FlowItem, Flow.__members__.values()))
        elif isinstance(flowopts, str):  # 'quit'
            # flowopts = (FlowItem.from_full_name(flowopts),)
            flowitems = (FlowItem(flowopts),)
        else:
            # flowopts = tuple(map(FlowItem.from_full_name, flowopts))
            flowitems = tuple(map(FlowItem, flowopts))
            if has_duplicates(flowitems):
                raise ValueError(f"{repr(self)}\nset_flow_opts(flowopts) | duplicate flowitems: {repr(flowitems)}")
        
        for flowitem in flowitems:
            self.items.store(flowitem)
            # if flowopt.value in self.items:
            #     raise ValueError(f'{repr(self)}\nset_special_options() | flowopt.value ({repr(flowopt.value)}) already exists in self.\nflowopt: {repr(flowopt)}.\nflowopts: {repr(flowopts)}')
            # self.items[flowopt.value] = flowopt.name
        return None
    
    def set_kw_options(self, **kw_opts: Union[str, tuple, bool]) -> None:
        """foo='bar', baz='continue'"""
        # darkprint(f'{self.__class__.__qualname__}.set_kw_options(kw_opts={repr(kw_opts)})')
        if not kw_opts:
            return
        if has_duplicates(kw_opts.values()):
            raise ValueError(f"{repr(self)}\nset_kw_options() duplicate kw_opts: {repr(kw_opts)}")
        if 'free_input' in kw_opts:
            raise DevError(f"{repr(self)}\nset_kw_options() | 'free_input' found in kw_opts, should have popped it out earlier.\nkw_opts: {repr(kw_opts)}")
        non_flow_kw_opts = dict()
        for kw in kw_opts:
            opt = kw_opts[kw]
            if kw in self.items:
                raise ValueError(f"{repr(self)}\nset_kw_options() | '{kw}' in kw_opts but was already in self.items.\nkw_opts: {repr(kw_opts)}")
            
            try:
                # flowitem = FlowItem.from_full_name(opt)
                flowitem = FlowItem(opt)
            except ValueError:
                non_flow_kw_opts[kw] = opt
            else:
                # not using self.items.store(flowitem) because kw isn't flowitem.identifier
                self.items[kw] = flowitem
        
        if not non_flow_kw_opts:
            return
        
        kw_items = KeywordItems(non_flow_kw_opts)
        
        self.items.update(**kw_items)
        # self.kw_opts = kw_opts
    
    def any_item(self, predicate: Callable[[MutableItem], Any]) -> bool:
        for item in self.items.values():
            if predicate(item):
                return True
        return False
    
    def all_yes_or_no(self) -> bool:
        
        for item in self.items.values():
            try:
                if not item.is_yes_or_no:
                    return False
            except AttributeError:
                print(colors.brightblack(f'{self.__class__.__qualname__}.all_yes_or_no() AttributeError with item.is_yes_or_no: {item} {type(item)}. Ignoring.'))
        return True
        
        # nonspecials = set(self.opts)
        # nonspecials.update(set(self.kw_opts.values()))
        # if not nonspecials:
        #     return False
        # all_yes_or_no = True
        # for nonspecial in nonspecials:
        #     if not re.fullmatch(YES_OR_NO, nonspecial):
        #         all_yes_or_no = False
        #         break
        # return all_yes_or_no
    
    # @cachedprop
    # def indexeditems(self) -> dict:
    #     # TODO: create an Items class (maybe also an MutableItem class?)
    #     indexeditems = dict()
    #     for idx, opt in enumerate(self.opts):
    #         indexeditems[str(idx)] = opt
    #
    #         # * self.kw_opts
    #     self._update_kw_opts_into_items(indexeditems)
    #
    #     # * self.flowopts
    #     self._update_special_opts_into_items(indexeditems)
    #
    #     return indexeditems
    
    # @cachedprop
    # def items(self) -> dict:
    #     # assumes duplicates between opts, special and kw were checked already
    #     items = dict()
    #     # * self.opts
    #     initials = [o[0] for o in self.opts]  # initials: 'w' 'w' 's' 'i' 'a'
    #     for idx, opt in enumerate(self.opts):
    #         initial: str = opt[0]
    #         duplicate_idxs = [jdx for jdx, jinitial in enumerate(initials) if jinitial == initial and jdx != idx]
    #         if not duplicate_idxs:
    #             items[initial] = opt
    #             continue
    #
    #         if len(duplicate_idxs) == 1:
    #             if initial.isupper():
    #                 # should handle like >= 2 duplicates
    #                 raise NotImplementedError("duplicate uppercase, probably one was uppercased in prev iteration: ", self.opts)
    #             # * opt = 'w', duplicates = ['w']
    #             #    transform one to 'W'
    #             upper = initial.upper()
    #             initials[idx] = upper
    #             items[upper] = opt
    #             dup_idx = duplicate_idxs[0]
    #             duplicate = initials[dup_idx]
    #             items[duplicate] = self.opts[dup_idx]
    #             continue
    #
    #         if len(duplicate_idxs) == 2:
    #             words = opt.split(' ')
    #             joined = ''.join(map(lambda s: s[0], words))
    #             if joined in initials:
    #                 for j in range(len(words)):
    #                     new_joined = joined[:j] + joined[j].upper() + joined[j:]
    #                     if new_joined not in initials:
    #                         joined = new_joined
    #                         break
    #                 else:
    #                     raise NotImplementedError("duplicate multi words with no unique uppercase permutation: ", self.opts)
    #
    #             items[joined] = opt
    #             dup_idx1, dup_idx2 = duplicate_idxs
    #             upper = initials[dup_idx1].upper()
    #             initials[dup_idx1] = upper
    #             items[upper] = self.opts[dup_idx1]
    #             items[initials[dup_idx2]] = self.opts[dup_idx2]
    #             continue
    #
    #         raise NotImplementedError("3 duplicate options with no word separators: ", self.opts)
    #
    #     # * self.kw_opts
    #     self._update_kw_opts_into_items(items)
    #
    #     # * self.flowopts
    #     self._update_special_opts_into_items(items)
    #
    #     return items
    
    # def _update_kw_opts_into_items(self, items: dict):
    #     for k, opt in self.kw_opts.items():
    #         if k in items:
    #             raise NotImplementedError("kw_opts clashes with items. displaying self.opts, self.kw_opts and items:",
    #                                       self.opts, self.kw_opts, items)
    #         items[k] = opt
    #
    # def _update_special_opts_into_items(self, items: dict):
    #     for spec in self.flowopts:
    #         if spec.value in items:
    #             raise NotImplementedError("flowopts clashes with items. displaying self.opts, self.kw_opts, flowopts and items:",
    #                                       self.opts, self.kw_opts, self.flowopts, items)
    #         items[spec.value] = spec.name


class NumOptions(Options):
    _itemscls = NumItems
    items: NumItems
    
    # def __init__(self, *opts: str):
    #     self.items = NumItems(opts)
    #     super().__init__(*opts)


class LexicOptions(Options):
    _itemscls = LexicItems
    items: LexicItems
    
    # def __init__(self, *opts: str):
    #     self.items = LexicItems(opts)
    #     super().__init__(*opts)
