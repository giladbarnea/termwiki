"""
python magic / duner / datamodel / descriptors
"""
from termwiki.colors import c, bg, i, h2, h3, h4, h5, h6
from termwiki.decorators import optional_subject

@optional_subject
def special_method_names(): # 3.3
    _DESCRIPTORS = f"""{h5('3.3.2.[2-3] Descriptors')}
    %python
    __get__(self, instance: T | None, owner: Type[T] = None)
      # 'instance' is None if accessed via the class (not instance).
    __set__(self, instance: T | None, value)
    __delete__(self, instance: T | None)
    /%python

    {h6('Bound / Unbound Methods')}
      %python
      >>> class A: pass
      >>> def f(self):
      ...     print('f: ', self)
      >>> a = A()
      # This:
      >>> A.f = f
      # Is equivalent to this:
      >>> a.f = f.__get__(a, A)
      >>> a.f
      <bound method f of <A object at 0x...>>
      >>> a.f()
      f:  <A object at 0x...>
      # This won't work; a.f() will TypeError (missing self):
      >>> a.f = f
      /%python

    {h6('@property')}
      %python
      >>> class Property:
      ...     def __init__(self, f):
      ...         self.f = f
      ...         self.f_setter = None
      ...     def __get__(self, instance, owner):
      ...         if instance is None: return self
      ...         return self.f(instance)
      ...     def __set__(self, instance, value):
      ...         self.f_setter(instance, value)
      ...     def setter(self, f):
      ...         self.f_setter = f
      ...         return self # Otherwise, x is set to None
      >>> class A:
      ...     _x = 42
      ...     @Property
      ...     def x(self):
      ...         return self._x
      ...     @x.setter
      ...     def x(self, value):
      ...         self._x = value
      # Note: a.__dict__['x'] raises KeyError
      /%python
    """
    _SLOTS = f"""{h5('3.3.2.4 __slots__')}"""

    # 3.3.8
    _ATTRIBUTES = f"""{h4('3.3.2 Customizing attribute access')}
    __getattribute__, __getattr__, __setattr__, __delattr__, __dir__
    %python
    def __getattribute__(self, key): # pseudo-code
        if key in self.__dict__:
            return self.__dict__[key]
        for cls in self.__class__.__mro__:
            if key in cls.__dict__:
                value = cls.__dict__[key]
                if hasattr(value, '__get__'):
                    return value.__get__(self, self.__class__)
                return value
        # Raising AttributeError or propagating super().__getattribute__(key) here does:
        if hasattr(self, '__getattr__'):
            return self.__getattr__(key)
        raise AttributeError(key)
    /%python
  
    {_DESCRIPTORS}

    {_SLOTS}
    """

    # 3.3.8
    _NUMERIC = f"""{h4('3.3.8 Numeric')}
    {c('If returns NotImplemented, __r<op>__ is invoked (except __pow__):')}
    __add__(self, other)           {c('+        ')}  __radd__(self, other)
    __sub__(self, other)           {c('-        ')}  __rsub__(self, other)
    __mul__(self, other)           {c('*        ')}  __rmul__(self, other)
    __matmul__(self, other)        {c('@        ')}  __rmatmul__(self, other)
    __truediv__(self, other)       {c('/        ')}  __rtruediv__(self, other)
    __floordiv__(self, other)      {c('//       ')}  __rfloordiv__(self, other)
    __mod__(self, other)           {c('%        ')}  __rmod__(self, other)
    __divmod__(self, other)        {c('divmod() ')}  __rdivmod__(self, other)
    __pow__(self, other[, modulo]) {c('**, pow()')}  __rpow__(self, other[, modulo])
    __lshift__(self, other)        {c('<<       ')}  __rlshift__(self, other)
    __rshift__(self, other)        {c('>>       ')}  __rrshift__(self, other)
    __and__(self, other)           {c('&        ')}  __rand__(self, other)
    __xor__(self, other)           {c('^        ')}  __rxor__(self, other)
    __or__(self, other)            {c('|        ')}  __ror__(self, other)

    x = x.__iadd__(y) <=> x += y (if defined)

    __neg__(self)      {c('-    ')}       __complex__(self)  {c('complex()')}
    __pos__(self)      {c('+    ')}       __int__(self)      {c('int()')}
    __abs__(self)      {c('abs()')}       __float__(self)    {c('float()')}
    __invert__(self)   {c('~    ')}       __index__(self)    {c('bin(), hex(), oct(); complex/int/float fallback')}
    __round__(self[, ndigits])     {c('round()')}
    __trunc__(self)                {c('math.trunc(); int fallback if no __int__ or __index__')}
    __floor__(self)                {c('math.floor()')}
    __ceil__(self)                 {c('math.ceil()')}
    """
    return f"""{h3('3.3 Special method names')}
{c('https://docs.python.org/3/reference/datamodel.html#special-method-names')}

  {h4('3.3.1 Basic customization')}
    __new__, __init__, ...
    {h5('Comparison')}
      Returning NotImplemented (also from numeric methods) makes interpreter
      try the __r<op>__ method on the operands.

  {_ATTRIBUTES}
  
  {_NUMERIC}
    """

@optional_subject
def datamodel():
    _STANDARD_TYPE_HIERARCHY = f"""{h3('3.2 The standard type hierarchy')}

  {h4('Callable special attributes')}
    __doc__: str?                       __code__
    __name__: str                       __globals__: dict {c('of defining module. Read-only')}
    __qualname__: str                   __dict__
    __module__: str?                    __closure__: tuple[cell]? {c('Read-only')}
    __annotations__: dict {c('"return" key')}  __get__
    __defaults__: tuple? {c('values')}         __call__
    __kwdefaults__: dict

  {h4('Module special attributes')}
    {c('https://docs.python.org/3/reference/import.html#import-related-module-attributes')}
    __doc__: str?
    __annotations__: dict
    __builtins__: module
    __file__: str {c("'/abs/path/to/file.py'")}
    __name__: str {c("'__main__' or 'termwiki.decorators.syntax'. Unique")}
    __loader__: SourceFileLoader
    __spec__: ModuleSpec? {c('__spec__.parent is a fallback for __package__')}
    __path__: list[str] {c("Unset for non-packages. ['/home/gilad/dev/termwiki/pages/decorators']")}
    __cached__: str? {c(".pyc file")}
    __package__: str? {c('if module is package: __package__ == __name__;')}
                               {c("otherwise, if top level: __package__ == '', else: 'termwiki.decorators'")}
                               {c("see https://peps.python.org/pep-0366/")}

  {h4('Custom classes')}
    Instance methods, not static methods, have __self__ attr (and __func__?)
    """
    return f"""{h2('Magic / Dunder / Data Model / Descriptors')}
{c('https://docs.python.org/3/reference/datamodel.html')}
{c('Plain list: pygments/lexers/python.py:266')}    
{_STANDARD_TYPE_HIERARCHY}
{special_method_names()}
{h3('__dict__ dir / vars / inspect.getmembers')}
  %python
  >>> dir(Console) == inspect.getmembers(Console) # True
  >>> vars(Console) == set(Console.__dict__) # True
  >>> dir(Console) > vars(Console) # True
  >>> dir(Console) - vars(Console)
      '__class__', '__delattr__', '__dir__', '__eq__', '__format__', '__ge__',
      '__getattribute__', '__gt__', '__hash__', '__init_subclass__', '__le__',
      '__lt__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__setattr__',
      '__sizeof__', '__str__', '__subclasshook__'
  >>> inspect.isroutine(Console) ==
  /%python
"""

datamodel.aliases = ['magic']