from pymake.targets.target import FilePath
from pymake.targets.wildcard import find_matching_target
from .targets import Target
from typing import Awaitable, Optional, Union, Set, Dict
from .cache import TimestampCache
import asyncio
from pathlib import Path
import os
import time


def make_sync(
    target: Target,
    *,
    cache: Optional[Union[TimestampCache, FilePath]] = '.pymake-cache',
    targets: Optional[Dict[str, Target]] = None,
    prefix_dir: FilePath = ''
):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(make(
        target, cache=cache, targets=targets, prefix_dir=prefix_dir))


async def make(
        target: Target,
        *,
        cache: Optional[Union[TimestampCache, FilePath]] = '.pymake-cache',
        targets: Optional[Dict[str, Target]] = None,
        prefix_dir: FilePath = ''
):
    assert targets  # TODO: import from calling module
    _targets = targets
    _prefix_dir = Path(prefix_dir)

    _cache = cache if cache is None or isinstance(cache, TimestampCache) \
        else TimestampCache(_prefix_dir / cache, targets) if targets else None
    loop = asyncio.get_event_loop()

    scheduled: Set[Target] = set()

    async def ensure_remake(target: Target):
        if target not in scheduled:
            scheduled.add(target)
            env_before = os.environ.copy()
            os.environ.clear()
            os.environ.update(target.env)
            try:
                if target.target:
                    target_path = Path(target.target)
                    if target_path.exists():
                        before = target_path.stat().st_mtime
                        await target.make()
                        assert target_path.stat().st_mtime > before, \
                            "output file did not change"  # TODO: custom error
                else:
                    await target.make()
                    if _cache is not None and target.do_cache:
                        _cache[target] = time.time()
            finally:
                os.environ.clear()
                os.environ.update(env_before)

    async def maybe_remake(target: Target) -> bool:
        "Recursively schedule target remakes if needed, returns if the target was remade"
        if not any(target.deps):
            await ensure_remake(target)
            return True

        target_edited = await target.edited()
        needs_remake = target_edited == float('inf')
        maybe_remaking: Set[Awaitable[bool]] = set()
        for dep in target.deps:
            if isinstance(dep, Path):
                if not dep.is_absolute():
                    dep = _prefix_dir / dep

                try:
                    if dep.stat().st_mtime > target_edited:
                        needs_remake = True
                    continue
                except FileNotFoundError:
                    dep = find_matching_target(dep, _targets)

            maybe_remaking.add(loop.create_task(maybe_remake(dep)))

        if any(await asyncio.gather(*maybe_remaking)):
            needs_remake = True

        if needs_remake:
            await ensure_remake(target)
            return True

        else:
            return False

    await maybe_remake(target)

    if _cache:
        _cache.save()
