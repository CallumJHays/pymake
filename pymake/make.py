from pymake.targets.target import FilePath
from pymake.targets.wildcard import find_matching_target
from .targets import Target
from typing import Awaitable, Optional, Union, Set, Dict
from .cache import TimestampCache
import asyncio
from pathlib import Path
import os
import time
from concurrent.futures import ProcessPoolExecutor


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

    scheduled: Dict[Target, Awaitable[float]] = {}
    
    loop = asyncio.get_event_loop()
    try:
        with ProcessPoolExecutor() as multiprocessor:
            async def maybe_remake(target: Target) -> bool:
                "Recursively schedule target remakes if needed, returns if the target was remade"
                if target in scheduled:
                    await scheduled[target]
                    return True
                
                if not any(target.deps):
                    needs_remake = True

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

                    maybe_remaking.add(asyncio.ensure_future(maybe_remake(dep)))

                if any(await asyncio.gather(*maybe_remaking)):
                    needs_remake = True

                if needs_remake:
                    scheduled[target] = asyncio.ensure_future(
                        loop.run_in_executor(multiprocessor, _remake, target))
                    await scheduled[target]
                    return True

                else:
                    return False

            await maybe_remake(target)
            
    finally:
        if _cache:
            _cache.save()

def _remake(target: Target) -> float:
    "Remake the given target, ensuring envvars and cwd is as expected. Returns the time the target was remade"

    env_before = os.environ.copy()
    os.environ.clear()
    os.environ.update(target.env)

    if not Path.cwd().samefile(target.cwd):
        os.chdir(target.cwd)

    async def process():
        after = None
        if target.target:
            target_path = Path(target.target)
            if target_path.exists():
                before = target_path.stat().st_mtime
                await target.make()
                after = target_path.stat().st_mtime
                # TODO: custom errors
                assert after != before, "output file did not change" 
                assert after > before, "output file went back in time"
        
        if not after:
            await target.make()
            after = time.time()
        
        return after
    
    try:
        made_time = asyncio.get_event_loop() \
            .run_until_complete(process())
    finally:
        os.environ.clear()
        os.environ.update(env_before)
    
    return made_time