from typing import Callable, Awaitable, Optional
from .targets.target import Target, FilePath, Dependencies
import inspect


def makes(
    out: Optional[FilePath],
    deps: Dependencies = [],
    do_cache: bool = True
) -> Callable[[Callable[[], Awaitable[None]]], Target]:

    def inner(fn: Callable[[], Awaitable[None]]):
        n_args = len(inspect.getargspec(fn).args)
        assert n_args < 2, "too many arguments for decorated function."

        class Fn(Target):  # type: ignore
            __name__ = "Fn_" + fn.__name__

            def __init__(self):
                super().__init__(out, deps, do_cache)

            async def make(self):
                await fn()

        return Fn()  # type: ignore
    return inner
