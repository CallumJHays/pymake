from pymake.targets.wildcard import find_matching_target
from .targets import Target
from typing import Awaitable, Optional, Union, Dict, Set, Tuple
from .environment import N_CPU_CORES
from .cache import Cache
import asyncio
from pathlib import Path
import time


def make(
    target: Target,
    *,
    cache: Optional[Union[Cache, str, Path]] = '.pymake-cache',
    n_workers: int = N_CPU_CORES,
):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(make_async(target, cache=cache))


async def make_async(
    target: Target,
    *,
    cache: Optional[Union[Cache, str, Path]] = '.pymake-cache',
    targets: Optional[Dict[str, Target]] = None
):
    assert targets  # TODO: import from calling module
    _targets = targets

    _cache = cache if cache is None or isinstance(cache, Cache) \
        else Cache(cache, targets) if targets else None
    loop = asyncio.get_event_loop()

    scheduled: Set[Target] = set()

    async def ensure_remake(target: Target):
        if target not in scheduled:
            scheduled.add(target)
            await target.make()

    async def maybe_remake(target: Target) -> Optional[Tuple[Target, float]]:
        "Recursively schedule target remakes if needed, returns the timestamp at which it was remade, or None if no remake was needed"
        if not any(target.deps):
            await ensure_remake(target)
            return target, time.time()

        maybe_remaking: Set[Awaitable[Optional[Tuple[Target, float]]]] = set()
        for dep in target.deps:
            if isinstance(dep, Path):
                dep = find_matching_target(dep, _targets)

            maybe_remaking.add(loop.create_task(maybe_remake(dep)))

        maybe_remade, pending = await asyncio.wait(maybe_remaking, return_when=asyncio.FIRST_EXCEPTION)
        for fut in maybe_remade:
            exc = fut.exception()
            if exc:
                raise exc

        assert not any(pending)

        needs_remake = False
        for fut in maybe_remade:
            res = fut.result()
            if res:
                needs_remake = True
                target, timestamp = res
                if _cache:
                    _cache[target] = timestamp

        if needs_remake:
            await ensure_remake(target)
            return target, time.time()

        else:
            return None

    await maybe_remake(target)

    if _cache:
        _cache.save()
