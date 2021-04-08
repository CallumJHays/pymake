from typing import Iterable, TYPE_CHECKING, Union, Optional, List, TypeVar
from pathlib import Path
from abc import ABC, abstractmethod
from copy import copy
import shutil

if TYPE_CHECKING:
    from ..context import ctx

FilePath = Union[str, Path]  # includes directories
Dependency = Union[FilePath, 'Target']
Dependencies = Union[Dependency, Iterable[Dependency]]

Self = TypeVar('Self', bound='Target')


class Target(ABC):
    "A target with one or many dependencies"

    def __init__(self, target: Optional[Union[str, FilePath]], deps: Dependencies, do_cache: bool = True):
        self.target = target
        self.deps: List[Union[Path, Target]] = \
            [Path(deps)] if isinstance(deps, str) \
            else [deps] if isinstance(deps, (Path, Target)) \
            else [Path(src) if isinstance(src, str) else src for src in deps]
        self.do_cache = do_cache

    @abstractmethod
    async def make(self):
        "Make the target"
        pass

    @abstractmethod
    async def clean(self):
        "'Undo' the make action if possible"
        if self.target is None:
            try:
                del ctx.cache[self]
            finally:
                return

        target_path = Path(self.target)
        if target_path.exists():
            if target_path.is_dir():
                shutil.rmtree(target_path, True)
            else:
                target_path.unlink()
            return

    async def newer_than(self, timestamp: float) -> bool:
        if self.target is None:
            return True

        assert not self.has_wildcard(), ""
        target_path = Path(self.target)
        try:
            edited = target_path.stat().st_mtime
        except FileNotFoundError:
            edited = ctx.cache[self]
        except KeyError:
            return True

        return edited > timestamp

    def matches(self, query: str) -> Optional[str]:
        # TODO: glob matching
        match = None
        return match

    def has_wildcard(self) -> bool:
        return \
            (self.target is not None and '%' in str(self.target)) \
            or any(
                '%' in str(dep) if isinstance(dep, Path)
                else dep.has_wildcard()
                for dep in self.deps
            )

    def __call__(self: Self, request: str) -> Self:
        "Create a new Target with any % wildcard replaced in target and all subdeps"
        if not self.has_wildcard():
            raise Exception(
                f"Attempted to replace '%' with '{request}' for target {self}, but the target has no '%' in its target or any of its dependencies")

        new = copy(self)
        new.target = str(new.target).replace('%', request) \
            if new.target else None
        new.deps = [
            dep(request) if isinstance(dep, Target) and dep.has_wildcard()
            else Path(str(dep).replace('%', request))
            for dep in new.deps
        ]
        return new
