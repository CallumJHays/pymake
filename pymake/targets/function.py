
from typing import Any, Awaitable, Callable, Optional, TYPE_CHECKING, Union
from .target import Target, FilePath, Depends
if TYPE_CHECKING:
    from ..context import Context

class Fn(Target):
    def __init__(
        self,
        target: Optional[Union[str, FilePath]],
        deps: Depends,
        fn: Callable[..., Awaitable[Any]],
        do_cache: bool = True,
    ):
        super().__init__(target, deps, do_cache)
        self.fn = fn

    async def make(self, ctx: 'Context'): # type: ignore
        await ctx.inject_and_run(self.fn)