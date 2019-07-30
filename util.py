"""Utility functions."""

from typing import Any, Callable, Dict, Iterable, TypeVar

def str_s(x: Any, default: str=None) -> str:
    """
    Safely construct a string.

    Instead of 'None' on None, default will be returned.
    """

    if x is None:
        return default

    try:
        return str(x)
    except:
        return default

def int_s(x: Any, base: int = 10, default: int=None) -> int:
    """Safely construct an integer."""

    try:
        return int(x, base=base)
    except (TypeError, ValueError):
        return default

def float_s(x: Any, default: float=None) -> float:
    """Safely construct a float."""

    try:
        return float(x)
    except (TypeError, ValueError):
        return default

def parse_int(x: str, base: int=10, default: int=None, aggressive: bool=False) -> int:
    """
    Attempt to parse an integer value.

    If aggressive is True, all characters will be stripped from x that do not
    constitute a digit of the specified base. Do not use unless x is known to
    contain exactly one integer value. Requires a base within [1, 36].
    """

    import re

    if aggressive:
        assert 1 <= base <= 36
        digits = '0-{0}{1}'.format(
            chr(ord('0') + min(base, 10) - 1),
            ('a-' + chr(ord('a') + base - 11)) if base > 10 else ''
        )
        x = re.sub('[^{0}]'.format(digits), '', x)

    return int_s(x, base=base, default=default)

def parse_ts(x: str, default=None) -> int:
    """
    Attempt to parse a simple timestamp.

    Timestamp may either be in h+:mm:ss or mm:ss format.

    Result is always in seconds.
    """

    import re

    match = re.match(r'(?:(\d+):)?(\d{2}):(\d{2})', x)
    if not match:
        return default

    (h, m, s) = tuple(int_s(x, default=0) for x in match.groups())
    if m > 60 or s > 60:
        return default

    return s + m*60 + h*3600

def index_s(x: Any, *indices, default=None) -> Any:
    """
    Attempt to obtain a value by indexing multiple times.

    If the indexing fails because of a TypeError, IndexError or KeyError, the
    default will be returned.
    """

    try:
        ret = x
        for index in indices:
            ret = ret[index]
        return ret
    except (TypeError, IndexError, KeyError):
        return default

def join_s(c: str, it: Iterable[str], default: str=None) -> str:
    """
    Safely join strings.

    If an item in the iterable is None, it will be replaced with the default
    before joining.

    All items that are none on joining will be omitted.
    """

    if default is None:
        return c.join(filter(lambda x: x is not None, it))
    return c.join(map(lambda x: x or default, it))

def run_sync(x, *args, **kwargs):
    """
    Execute a function synchronously.

    If x is an awaitable or a future, x is awaited and the result is returned.

    If x is a coroutine function, x is invoked with (*args, **kwargs), and the
    resulting coroutine is awaited and the result is returned.

    If x is some other function, x is invoked with (*args, **kwargs), and the
    result is returned.
    """

    import asyncio

    if asyncio.iscoroutine(x):
        pass
    elif asyncio.iscoroutinefunction(x):
        x = x(*args, **kwargs)
    elif callable(x):
        return x(*args, **kwargs)

    x = asyncio.ensure_future(x)
    loop = asyncio.get_event_loop()
    ret = loop.run_until_complete(x)
    return ret

T, K = TypeVar('T'), TypeVar('K')

def unique(iterable: Iterable[T], get_key: Callable[[T], K] = lambda x: x) -> Iterable[T]:
    """
    Iterate over all unique values in the input sequence.

    Every element with a unique key will be yielded exactly once, and the
    order of these elements will be preserved.

    get_key will be used to obtain the key for every object in the iterable.
    """

    seen = set()
    for x in iterable:
        if get_key(x) in seen:
            continue
        seen.add(x)
        yield x

def coalesced(iterable: Iterable[T], eq: Callable[[T, T], bool] = lambda x,y: x == y) -> Iterable[T]:
    """
    Iterate over the coalesced sequence.

    Only the first element in any consecutive run of elements of the same
    equivalency class will be yielded, all following items in the run will be
    discarded.
    """

    it = iter(iterable)
    last = next(it)
    yield last
    while True:
        cur = next(it)
        if eq(cur, last):
            continue
        last = cur
        yield cur

def has_brotli():
    """Check whether brotli compression is available."""

    try:
        import brotli
        return True
    except ModuleNotFoundError:
        return False

def is_valid_encoding(encoding: str) -> bool:
    """Check whether the specified encoding exists."""

    try:
        ''.encode(encoding)
        return True
    except LookupError:
        return False

def get_default_headers() -> Dict[str, str]:
    """Get the default headers for YT queries."""

    # Defaults are always accepted.
    accept_encodings = [
        'gzip',
        'deflate'
    ]

    # If brotlipy is installed, brotli is also accepted.
    if has_brotli():
        accept_encodings.append('br')

    return {
        'Host': 'www.youtube.com',
        # We do not need to lie about ourselves.
        'User-Agent': 'Python/3.6 aiohttp/3.5.4',
        # We cannot deal with anything else.
        'Accept-Encoding': ', '.join(accept_encodings)
    }