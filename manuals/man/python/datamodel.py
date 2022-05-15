"""
python dunder
"""
from manuals.colors import c


def numeric():
    return f"""
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