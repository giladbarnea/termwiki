# class CachingGenerator(Generic[T]):
#     # todo: i'm considering caching much simpler, like cached_property
#     instance: T
#     generator: Callable[[T, ...], Iterable[I]]
#     _cacher: Callable[[T, I], ...]
#     _cache_getter: Callable[[T], Iterator[I]]
#
#     def __init__(self, generator: Callable[[T, ...], Iterable[I]]):
#         self.generator = generator
#         self.instance: T = None
#         self._cacher = None
#         self._cache_getter = None
#
#     def __repr__(self):
#         repred = f'{self.__class__.__name__}({self.generator})'
#         if self.instance:
#             repred += f' (instance={repr(self.instance)[:40]}...)'
#         return repred
#
#     def __get__(self, instance: T, owner: Type[T]):
#         if instance is not None:
#             # if self.instance:
#             #     assert self.instance is instance, f'{self} is not bound to {instance}'
#             self.instance = instance
#         return self
#
#     def __call__(self, *args, **kwargs):
#         if self.instance is None:
#             raise AttributeError(f'{self.__class__.__name__} is not bound to an instance')
#
#         if getattr(self.instance, f'__traverse_exhausted__', False):
#             # log.warning(f'{self.instance.__class__.__qualname__}.{self.generator.__name__} is exhausted')
#             yield from self._cache_getter(self.instance)
#             return
#
#         for page in self.generator(self.instance, *args, **kwargs):
#             self._cacher(self.instance, page)
#             yield page
#
#         setattr(self.instance, f'__traverse_exhausted__', True)
#
#     def set_cacher(self, cacher: Callable[[T, I], ...]):
#         self._cacher = cacher
#
#     def set_cache_getter(self, cache_getter: Callable[[T], Iterator[I]]):
#         self._cache_getter = cache_getter
