from .targets.target import FilePath
from typing import Optional
from asyncio.subprocess import create_subprocess_shell, PIPE
from subprocess import CalledProcessError
from .utils import unindent
from .logging import logger
import inspect


async def sh(
    script: str,
    cwd: FilePath = '.',
    silent: bool = False
) -> Optional[bytes]:
    # TODO: print to terminal
    script = unindent(script)
    if not silent:
        frame = inspect.stack()[1]
        logger.info(f'Running "{script}"', extra=dict(frame=frame))

    process = await create_subprocess_shell(
        unindent(script),
        cwd=cwd,
        stderr=PIPE, stdout=PIPE
    )
    stdout, stderr = await process.communicate()
    assert process.returncode is not None
    if process.returncode != 0:
        raise ShellExecError(process.returncode, script,
                             stdout.decode(), stderr.decode())

    if not silent:
        output = (
            f'{script}\n{stdout.decode().strip()}'
        ).replace('\n', '\n  >> ')
        logger.info(output, extra=dict(frame=frame))  # type: ignore
    return stdout if any(stdout) else None


class ShellExecError(CalledProcessError):
    pass
