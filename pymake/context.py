from typing import Any, Awaitable, Callable, TYPE_CHECKING, Type
from inspect import getfullargspec
from .utils import unindent

if TYPE_CHECKING:
    from .targets.target import Dependencies, Dependency
    from .cache import TimestampCache


class ctx:
    "singleton context object"

    # the build cache with build timestamps and durations
    cache: 'TimestampCache'

    # the string that matches the % for any @makes fn
    match: str
    # the full string / Path / instance of the target (with the % replaced)
    target: 'Dependency'
    # all deps (with the %s replaced)
    deps: 'Dependencies'


async def inject_and_run(ctx: ctx, fn: Callable[..., Awaitable[Any]]):
    spec = getfullargspec(fn)
    kwargs = {}
    for arg in spec.args:
        try:
            kwargs[arg] = getattr(ctx, arg)
        except AttributeError:
            raise Exception(unindent(f"""
                Property '{arg}' not available in pymake context, but is required by target make function: {fn}
                Available properties are: {[attr for attr in dir(ctx) if not attr.startswith('_')]}. Please see documentation for more info.
            """))

    await fn(**kwargs)
