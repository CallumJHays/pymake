from typing import Any, Awaitable, Callable, Optional, TYPE_CHECKING, get_type_hints
from inspect import isclass
from .utils import unindent

if TYPE_CHECKING:
    from .targets.target import Dependencies, FilePath
    from .cache import TimestampCache


class Context:
    def __init__(
        self,
        cache: Optional['TimestampCache'],
        match: Optional[str],
        out: Optional['FilePath'],
        deps: Optional['Dependencies']
    ):
        if cache:
            self.cache = cache
        if match:
            self.match = match
        if out:
            self.out = out
        if deps:
            self.deps = deps


    async def inject_and_run(self, fn: Callable[..., Awaitable[Any]]):
        kwargs = {}
        for arg, type in get_type_hints(fn).items():
            if arg is 'ctx':
                assert type is Context
                kwargs['ctx'] = self
            try:
                kwargs[arg] = getattr(self, arg)
                if isclass(type):
                    assert isinstance(kwargs[arg], type), \
                        f"Expcected context object {arg} to be of type {type} but instead found {kwargs[arg]}"

            except AttributeError:
                raise Exception(unindent(f"""
                    Property '{arg}' not available in pymake context, but is required by target make function: {fn}
                    Available properties are: {[attr for attr in dir(self) if not attr.startswith('_')]}. Please see documentation for more info.
                """))

        await fn(**kwargs)
