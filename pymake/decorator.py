from typing import Any, Callable, Awaitable, Optional
from .targets.target import Target, FilePath, Depends
import inspect


def makes(
    out: Optional[FilePath],
    deps: Depends = [],
    do_cache: bool = True
) -> Callable[[Callable[..., Awaitable[Any]]], Target]:

    def inner(fn: Callable[..., Awaitable[Any]]):
        spec = inspect.getfullargspec(fn)

        class Fn(Target):  # type: ignore
            __name__ = "Fn_" + fn.__name__

            def __init__(self):
                super().__init__(out, deps, do_cache)

            async def make(self, **kwargs):
                kwargs_used: Any = {
                    name: kwargs[name] for name in spec.args
                }
                await fn(**kwargs_used)

        return Fn()  # type: ignore
    return inner
