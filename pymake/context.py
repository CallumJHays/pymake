from .targets.target import Dependencies, Dependency
from .cache import Cache


class ctx:
    "context object"

    # the build cache with build timestamps and durations
    cache: Cache

    # the string that matches the % for any @makes fn
    match: str
    # the full string / Path / instance of the target (with the % replaced)
    target: Dependency
    # all deps (with the %s replaced)
    deps: Dependencies
