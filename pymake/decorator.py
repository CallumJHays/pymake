from typing import Any, Callable, Awaitable, Optional
from .targets.target import Target, FilePath, Depends
from .targets.function import Fn


def makes(
    target: Optional[FilePath],
    deps: Depends = [],
    do_cache: bool = True
) -> Callable[[Callable[..., Awaitable[Any]]], Target]:

    def inner(fn: Callable[..., Awaitable[Any]]):
        return Fn(target, deps, fn, do_cache)
        
    return inner
