from typing import Any, Iterable, List, Union, Optional, TypeVar, TYPE_CHECKING
from pathlib import Path
from abc import ABC, abstractmethod
from copy import copy
import shutil
import inspect
import os

if TYPE_CHECKING:
    from ..cache import TimestampCache

Dependencies = List[Union[Path, 'Target']]  # stored dependencies

FilePath = Union[str, Path]  # includes directories
Dependency = Union[FilePath, 'Target']
Depends = Union[Dependency, Iterable[Dependency]]  # Input Dependencies

Self = TypeVar('Self', bound='Target')


class Target(ABC):
    "A target with any number of dependencies"

    def __init__(self, target: Optional[Union[str, FilePath]], deps: Depends, do_cache: bool = True):
        if isinstance(target, str):
            assert not any(c in target for c in ' \t\n'), \
                "target should not contain any whitespace characters"
            assert not "*" in target, \
                "Only \"%\" wildcards are supported for target names"

        # make all paths relative to the source file of instantiation
        for frame in inspect.stack():
            if not isinstance(frame.frame.f_locals.get('self', None), Target):
                self.cwd = Path(frame.filename).parent
                break
        else:
            raise Exception("Couldn't find cwd where this target is defined")

        self.target = target if target else None
        self.deps: Dependencies = \
            [Path(deps)] if isinstance(deps, str) \
            else [deps] if isinstance(deps, (Path, Target)) \
            else [Path(src) if isinstance(src, str) else src for src in deps]
        self.do_cache = do_cache and any(self.deps)
        self.env = os.environ.copy()

    @abstractmethod
    async def make(self):
        "Make the target"
        pass

    async def clean(self, cache: 'TimestampCache'):
        "'Undo' the make action if possible"
        if self.target:
            target_path = Path(self.target)
            if target_path.exists():
                if target_path.is_dir():
                    shutil.rmtree(target_path, True)
                else:
                    target_path.unlink()
        else:
            cache.pop(self, None)

    async def edited(self) -> float:
        "Return POSIX timestamp at which this was last edited. Should return float('inf') if unable to tell."
        if self.target is None:
            return float('inf')

        assert not self.has_wildcard()
        target_path = Path(self.target)
        try:
            return target_path.stat().st_mtime
        except FileNotFoundError:
            return float('inf')

    def matches(self, query: str) -> Optional[str]:
        # TODO: glob matching
        match = None
        return match

    def has_wildcard(self) -> bool:
        return self.target is not None and '%' in str(self.target)

    def __call__(self: Self, request: FilePath) -> Self:
        "Create a new Target with any % wildcard replaced in target and all subdeps"
        if not self.has_wildcard():
            raise Exception(
                f"Attempted to replace '%' with '{request}' for target {self}, but the target has no '%' in its target or any of its dependencies")

        new = copy(self)
        new.target = str(new.target).replace('%', str(request)) \
            if new.target else None
        new.deps = [
            (dep(request) if dep.has_wildcard() else dep) if isinstance(dep, Target)
            else Path(str(dep).replace('%', str(request)))
            for dep in new.deps
        ]
        return new

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{f'({self.target})' if self.target else ''}"
