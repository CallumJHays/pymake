from .targets.target import FilePath
from pathlib import Path
from typing import Optional
from asyncio.subprocess import create_subprocess_shell, PIPE
from subprocess import CalledProcessError


async def sh(
    script: str,
    shell_exec: str = '/usr/bin/bash -c "{}"',
    cwd: FilePath = Path(__file__)
) -> Optional[bytes]:
    # TODO: print to terminal
    process = await create_subprocess_shell(
        shell_exec.format(script, cwd=cwd),
        stderr=PIPE, stdout=PIPE
    )
    stdout, stderr = await process.communicate()
    assert process.returncode
    if process.returncode != 0:
        raise ShellExecError(process.returncode, stderr)
    return stdout if any(stdout) else None


class ShellExecError(CalledProcessError):
    pass
