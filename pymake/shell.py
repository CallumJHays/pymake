from .targets.target import FilePath
from typing import Optional
from asyncio.subprocess import create_subprocess_shell, PIPE
from subprocess import CalledProcessError
from .utils import unindent
from .logging import logger


async def sh(
    script: str,
    cwd: FilePath = '.',
    silent: bool = False
) -> Optional[bytes]:
    # TODO: print to terminal
    script = unindent(script)
    process = await create_subprocess_shell(
        unindent(script),
        cwd=cwd,
        stderr=PIPE, stdout=PIPE
    )
    if not silent:
        logger.info(f"Running {script}")
    stdout, stderr = await process.communicate()
    assert process.returncode is not None
    if process.returncode != 0:
        raise ShellExecError(process.returncode, stderr.decode())

    if not silent:
        output = ('\n' + stdout.decode().strip()).replace('\n', '\n  >> ')
        logger.info(output)
    return stdout if any(stdout) else None


class ShellExecError(CalledProcessError):
    pass
