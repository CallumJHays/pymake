from typing import Any, Callable, Dict, Iterable, Union, Optional, ModuleType, List, Awaitable, TypeVar, Tuple, cast, overload, Type
from pathlib import Path
from abc import ABC, abstractmethod
import json
from concurrent.futures import ProcessPoolExecutor
import asyncio
from subprocess import check_output
import logging
import time
import inspect

__all__ = [
    'FilePath', 'Dependency', 'Dependencies',
    'Target', 'CacheStamped', 'File', 'Compile', 'Makefile',
    'makes', 'writes', 'depends', 'command'
]

FilePath = Union[str, Path]  # includes directories
Dependency = Union[FilePath, 'Target']
Dependencies = Union[Dependency, Iterable[Dependency]]


class Target(ABC):
    "A target with one or many dependencies"

    def __init__(self, deps: Dependencies):
        self.deps: List[Union[Path, Target]] = \
            [Path(deps)] if isinstance(deps, str) \
            else [deps] if isinstance(deps, (Path, Target)) \
            else [Path(src) if isinstance(src, str) else src for src in deps]

    @abstractmethod
    def edited(self) -> float:
        "Return the POSIX timestamp (secs since epoch at which the target was last edited."
        pass

    @abstractmethod
    def make(self):
        "Make the target"
        pass


class CacheStamped(Target):
    "A target that is timestamped to the .pymake-cache file"

    def __init__(self, deps: Dependencies):
        super().__init__(deps)
        self.name: Optional[str] = None

    def edited(self):
        return Context.timestamps.get(self, 0)


class Command(Target):
    def __init__(self):
        super().__init__([])

    def edited(self):
        return 0


class FileTarget(Target):
    def __init__(
        self,
        target: FilePath,
        deps: Dependencies
    ):
        super().__init__(deps)
        self.target = Path(target)

    def edited(self):
        return self.target.stat().st_mtime


class Compile(FileTarget):
    def make(self):
        pass


class Makefile(FileTarget):
    def __init__(
        self,
        target: FilePath,
        makefile: FilePath,
        deps: Dependencies
    ):
        super().__init__(target, deps)
        self.makefile = makefile
        self.deps.insert(0, Path(makefile))

    def make(self):
        sh(f"make --directory={self.makefile} -j{Context.n_workers}")


T = TypeVar('T')
Tgt = TypeVar('Tgt')


@overload
def makes(out: FilePath, deps: Dependencies = []) -> Callable[[Callable[[FilePath, Dependencies], None]], FileTarget]:
    ...


@overload
def makes(out: None, deps: Dependencies = []) -> Callable[[Callable[[Dependencies], None]], CacheStamped]:
    ...


@overload
def makes(out: None, deps: None) -> Callable[[Callable[[], None]], Command]:
    ...


def makes(out: Optional[FilePath] = None, deps: Dependencies = []):  # type: ignore
    def inner(fn: Callable[..., None]):
        Base = FileTarget if out \
            else CacheStamped if deps \
            else Command

        n_args = len(inspect.getargspec(fn).args)
        assert n_args < 3, "too many arguments for decorated function."

        class Fn(Base):  # type: ignore
            __name__ = "Fn_" + fn.__name__

            def make(self):
                if n_args == 2:
                    fn(out, deps)
                elif n_args == 1:
                    fn(deps)
                else:
                    fn()

                fn(out, deps)

        return Fn()  # type: ignore
    return inner


async def run_async(
    makefile: ModuleType,
    target: Dependency,
    cache_path: Optional[str] = '.pymake-cache',
    n_workers: int = 4
):
    assert n_workers > 0
    Context.n_workers = n_workers

    path2target: Dict[str, Target] = {}
    for name in dir(makefile):
        dep = getattr(makefile, name)
        if not isinstance(dep, Target):
            continue

        if isinstance(dep, CacheStamped):
            dep.name = name

        # if the dep is a file also register the absolute filepath
        # use absolute to work better with external PyMakefiles
        if isinstance(dep, FileTarget):
            path2target[str(dep.target.absolute())] = dep

    try:
        if cache_path is not None:
            Context.load_cache(cache_path)
    except:
        pass

    if not isinstance(target, Target):
        abs_target_path = str(Path(target).absolute())
        try:
            target = path2target[abs_target_path]
        except KeyError as e:
            raise e  # TODO: helpful error message (levenshtein distance)

    with ProcessPoolExecutor(n_workers) as executor:
        loop = asyncio.get_event_loop()
        target2future: Dict[Target, Awaitable[Any]] = {}

        async def ensure_remake(target: Target):
            if target not in target2future:
                target2future[target] = fut = loop.run_in_executor(
                    executor,
                    with_duration(target.make)
                )
                duration, _ = await fut
                Context.durations[target] = duration

        async def maybe_remake(target: Target) -> bool:
            "Recursively schedule target remakes if needed, returns True if the target needed remaking"
            if not any(target.deps):
                await ensure_remake(target)
                return True

            edited = target.edited()
            needs_remake = False

            for dep in target.deps:
                if isinstance(dep, Target):
                    remade = await maybe_remake(dep)

                    if remade:
                        # update context
                        now = time.time()
                        if isinstance(dep, CacheStamped):
                            Context.timestamps[dep] = now

                        needs_remake = True

                else:
                    dep_target = path2target.get(str(dep.absolute()))

                    dep_is_newer = maybe_remake(dep_target) if dep_target \
                        else dep.stat().st_mtime > edited

                    if dep_is_newer:
                        needs_remake = True

            if needs_remake:
                await ensure_remake(target)

            return needs_remake

        await maybe_remake(target)

        if cache_path:
            Context.write_cache(cache_path)


def run(makefile: ModuleType, target: Dependency, n_workers: int = 4):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_async(makefile, target, n_workers=n_workers))


def sh(
    script: str,
    shell_exec: str = '/usr/bin/bash -c "{}"'
) -> Optional[bytes]:
    output = check_output(shell_exec.format(script), shell=True)
    return output if any(output) else None


def with_duration(fn: Callable[..., T]) -> Callable[..., Tuple[float, T]]:
    def wrapper(*args: Any, **kwargs: Any):
        before = time.time()
        res = fn(*args, **kwargs)
        return (
            time.time() - before,
            res
        )
    return wrapper


class Context:
    # loaded in run()
    n_workers: int
    targets: Dict[str, Target]
    # loaded from cache / altered by Targets
    timestamps: Dict[CacheStamped, float]
    durations: Dict[Target, float]

    @classmethod
    def write_cache(cls, path: FilePath):
        with open(path, 'w') as f:
            json.dump({
                'timestamps': {
                    name: cls.timestamps[target]
                    for name, target in cls.targets.items()
                    if isinstance(target, CacheStamped) and target in cls.timestamps
                },
                'duration': {
                    name: cls.durations[target]
                    for name, target in cls.targets.items()
                    if target in cls.durations
                }
            }, f)

    @classmethod
    def load_cache(cls, path: FilePath):
        with open(path, 'r') as f:
            cache = json.load(f)

            for name, timestamp in cache['timestamps']:
                if name in cls.targets:
                    target = cls.targets[name]

                    if isinstance(target, CacheStamped):
                        cls.timestamps[target] = float(timestamp)
                    else:
                        logging.debug(
                            f'cached target of name {name} has changed type and no longer needs its timestamp cached')

            for name, average_maketime in cache['duration']:
                if name in cls.targets:
                    target = cls.targets[name]
                    cls.durations[target] = float(average_maketime)
                else:
                    logging.debug(
                        f"target {name} is no longer defined in the PyMakefile. Discarding cache info.")


if __name__ == "__main__":
    import importlib
    makefile = importlib.import_module('PyMakefile')
    run(makefile, 'all')


# def _levenshtein_distance(token1: str, token2: str) -> float:
#     "Returns a scalar representing a 'difference score' between two strings"
#     # ripped from https://blog.paperspace.com/implementing-levenshtein-distance-word-autocomplete-autocorrect/

#     distances = [[0] * (len(token2) + 1)] * (len(token1) + 1)

#     for t1 in range(len(token1) + 1):
#         distances[t1][0] = t1

#     for t2 in range(len(token2) + 1):
#         distances[0][t2] = t2

#     a = 0
#     b = 0
#     c = 0

#     for t1 in range(1, len(token1) + 1):
#         for t2 in range(1, len(token2) + 1):
#             if (token1[t1-1] == token2[t2-1]):
#                 distances[t1][t2] = distances[t1 - 1][t2 - 1]
#             else:
#                 a = distances[t1][t2 - 1]
#                 b = distances[t1 - 1][t2]
#                 c = distances[t1 - 1][t2 - 1]

#                 if (a <= b and a <= c):
#                     distances[t1][t2] = a + 1
#                 elif (b <= a and b <= c):
#                     distances[t1][t2] = b + 1
#                 else:
#                     distances[t1][t2] = c + 1

#     return distances[len(token1)][len(token2)]
