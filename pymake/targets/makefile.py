from typing import Dict, Optional
from pathlib import Path
from ..shell import sh, ShellExecError

from .target import FilePath, Target, Dependencies
from ..environment import N_CPU_CORES


class Makefile(Target):
    def __init__(
        self,
        directory: FilePath,
        *,
        target: Optional[str] = None,
        makefile: FilePath = 'Makefile',
        vars: Dict[str, str] = {},
        extra_deps: Dependencies = [],
        n_workers: int = N_CPU_CORES,
        exe: FilePath = "make",
        clean_target: str = 'clean'
    ):
        super().__init__(None, extra_deps)
        self.directory = directory
        self.target = target
        self.makefile = makefile
        self.vars = vars
        self.deps.insert(0, Path(makefile))
        self.n_workers = n_workers
        self.exe = exe
        self.clean_target = clean_target

    async def make(self):
        await self._execute(self.target or "")

    async def clean(self):
        await self._execute(self.clean_target)

    async def newer_than(self, timestamp: float) -> bool:
        try:
            # check if target is up-to-date
            # https://www.gnu.org/software/make/manual/html_node/Instead-of-Execution.html#Instead-of-Execution
            await self._execute(f"-q {self.target or ''}")
            return False  # target was up-to-date

        except ShellExecError:
            return True  # target was not up-to-date

    async def _execute(self, target: str):
        makefile_vars = ' '.join(
            f'{name}={item}' for name, item in self.vars.items())
        await sh(f"{self.exe} --directory={self.directory} -j{self.n_workers} {target} {makefile_vars}")
