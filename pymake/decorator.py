from typing import Any, Callable, Awaitable, Optional
from .targets.target import Target, FilePath, Dependencies
from .context import ctx, inject_and_run


def makes(
    out: Optional[FilePath],
    deps: Dependencies = [],
    do_cache: bool = True
) -> Callable[[Callable[..., Awaitable[Any]]], Target]:

    def inner(fn: Callable[..., Awaitable[Any]]):
        class Fn(Target):  # type: ignore
            __name__ = "Fn_" + fn.__name__

            def __init__(self):
                super().__init__(out, deps, do_cache)

            async def make(self):
                await inject_and_run(ctx, fn)

        return Fn()  # type: ignore
    return inner
