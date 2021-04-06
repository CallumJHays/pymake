from importlib import import_module
from typing import Any, Callable, Dict, Iterable, Set, Union, Optional, List, TypeVar, Tuple, overload
from pathlib import Path
from abc import ABC, abstractmethod
import json
from concurrent.futures import ProcessPoolExecutor
import asyncio
from subprocess import check_output
import logging
import time
import inspect
import click

__all__ = [
    'FilePath', 'Dependency', 'Dependencies',
    'Target', 'CacheStamped', 'File', 'Compile', 'Makefile',
    'makes', 'match', 'run', 'run_async'
]

here = Path(__file__)

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

    def matches(self, query: FilePath) -> Optional[str]:
        # TODO: glob matching
        match = None
        return match


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


# the string that matches the % for any @makes fn
match: Optional[str] = None


MakesFn = Union[
    Callable[[str], None],
    Callable[[], None]
]


@overload
def makes(out: FilePath, deps: Dependencies = []) -> Callable[[MakesFn], FileTarget]:
    ...


@overload
def makes(out: None, deps: Dependencies) -> Callable[[MakesFn], CacheStamped]:
    ...


@overload
def makes(out: None, deps: None) -> Callable[[MakesFn], Command]:
    ...


def makes(out: Optional[FilePath], deps: Dependencies = []):  # type: ignore
    def inner(fn: Callable[..., None]):
        Base = FileTarget if out \
            else CacheStamped if deps \
            else Command

        n_args = len(inspect.getargspec(fn).args)
        assert n_args < 2, "too many arguments for decorated function."

        class Fn(Base):  # type: ignore
            __name__ = "Fn_" + fn.__name__

            def make(self):
                if n_args == 1:
                    fn(match)
                else:
                    fn()

        return Fn()  # type: ignore
    return inner


async def make_async(
    target: Target,
    *,
    cache_path: Optional[str] = '.pymake-cache',
    n_workers: int = 4
):
    assert n_workers > 0
    Context.n_workers = n_workers
    # secs of previous make time at which to use a worker instead of main process
    USE_WORKER_THRESHOLD = 0.5

    try:
        if cache_path is not None:
            Context.load_cache(cache_path)
    except:
        pass

    with ProcessPoolExecutor(n_workers) as executor:
        loop = asyncio.get_event_loop()
        scheduled: Set[Target] = set()

        async def ensure_remake(target: Target):
            if target not in scheduled:
                scheduled.add(target)
                duration = Context.durations.get(target)
                timed_make = with_duration(target.make)

                # should we use a subprocess? what would be faster?
                # assume that most makes take more than the threshold
                use_subprocess = duration is None or duration > USE_WORKER_THRESHOLD
                if use_subprocess:
                    duration, _ = await loop.run_in_executor(
                        executor,
                        timed_make
                    )
                else:
                    duration, _ = timed_make()
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


def make(
    target: Target,
    *,
    cache_path: Optional[str] = '.pymake-cache',
    n_workers: int = 4,
):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(make_async(
        target,
        cache_path=cache_path,
        n_workers=n_workers
    ))


def sh(
    script: str,
    shell_exec: str = '/usr/bin/bash -c "{}"',
    cwd: Path = here
) -> Optional[bytes]:
    output = check_output(shell_exec.format(script), shell=True, cwd=cwd)
    return output if any(output) else None


STANDARD_MAKEFILE = Path('PyMakefile.py')


class NoTargetMatchError(Exception):
    pass


class MultipleTargetsMatchError(Exception):
    pass


@click.command()
@click.argument("request")
@click.argument("--makefile", "-m", default='PyMakefile.py')
@click.argument("--cache", "-c", default='.pymake-cache')
@click.argument("--n-workers", "-j", default=4)
def run(
    request: str,
    makefile: str = 'PyMakefile.py',
    cache_path: str = '.pymake-cache',
    n_workers: int = 4
):
    "Run the makefile as a command-line app, handling arguments correctly"

    module = import_module(makefile)

    try:
        target = getattr(module, request)
        assert isinstance(target, Target), \
            f"Expected requested target to be of class Target, but instead found {target.__class__}"

    except AttributeError:
        # no target was matched directly.
        # Perhaps this will match the output of a FileTarget?
        matching: Set[Target] = set()
        for name in dir(module):
            export = getattr(module, name)
            if isinstance(export, FileTarget):
                match = export.matches(request)
                if match:
                    matching.add(export)

        if not any(matching):
            # TODO: levenshtein debugging assistance
            raise NoTargetMatchError(
                f"No targets matches the request '{request}'")
        elif len(matching) > 1:
            raise MultipleTargetsMatchError(
                f"Multiple targets match the request '{request}':\n" +
                "\n".join(f"    - {match}" for match in matching)
            )
        else:
            target = matching.pop()

    make(target, cache_path=cache_path, n_workers=n_workers)


T = TypeVar('T')


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

    @ classmethod
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

    @ classmethod
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
