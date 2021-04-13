import click
from runpy import run_path
import asyncio
from typing import Dict, List
from pathlib import Path

from .targets.target import FilePath, Target, Union
from .targets.wildcard import NoTargetMatchError, find_matching_target
from .make import make_sync
from .decorator import makes
from .logging import logger, YELLOW, RESET, GREY
from .utils import unindent


def run(
    makefile: str,
    request: str,
    cache: str = '.pymake-cache',
    no_cache: bool = False,
    loglevel: Union[int, str] = "WARNING"
):
    logger.setLevel(loglevel)
    exports = run_path(makefile)

    # collect all targets
    targets = {
        name: val for name, val
        in exports.items()
        if isinstance(val, Target)
    }

    try:
        target = getattr(exports, request)
        assert isinstance(target, Target), \
            f"Expected requested target to be of class Target, but instead found {target.__class__}"

    except AttributeError:
        # no target was matched directly.
        # Perhaps this will match the output of a FileTarget?
        try:
            target = find_matching_target(request, targets)
        except NoTargetMatchError as e:
            if request == 'help':
                target = default_help(targets)
            elif request == 'clean':
                target = default_clean(targets)
            elif request.startswith('clean-'):
                assert False
            else:
                raise e

    make_sync(target, cache=None if no_cache else cache,
              targets=targets, prefix_dir=Path(makefile).parent)


def cli(makefile: FilePath, loglevel: Union[int, str] = "WARNING"):
    """Run the makefile as a command-line app, handling arguments correctly
    Requires the makefile to be passed in. Intended to be run as such in a PyMakefile.py:
    ```python
    if __name__ == "__main__":
        cli(__file__)
    ```
    """
    # not DRY enough... but whatever
    @click.command()
    @click.argument("request", default="help")
    @click.option("--no-cache", default=False)
    @click.option("--cache", default='.pymake-cache')
    def cmd(*args, **kwargs):
        run(*args, makefile=str(makefile),  # type: ignore
            loglevel=loglevel, **kwargs)  # type: ignore
    return cmd()


@click.command()
@click.argument("request", default="help")
@click.option("--makefile", "-m", default='PyMakefile.py')
@click.option("--loglevel", "-l", default='WARNING')
@click.option("--no-cache", default=False)
@click.option("--cache", default='.pymake-cache')
def cli_shell(*args, **kwargs):
    "Run the makefile as a command-line app, handling arguments correctly"
    run(*args, **kwargs)


def default_help(targets: Dict[str, Target]):
    target2names: Dict[Target, List[str]] = {}
    for name, target in targets.items():
        target2names.setdefault(target, []).append(name)

    @makes('help')
    async def help():
        print('All Targets:')
        for target, names in target2names.items():
            spec_str = f"    - {'/'.join(f'{YELLOW}{name}{RESET}' for name in names)} {repr(target)}"
            spec_str += ':'
            for dep in target.deps:
                spec_str += f" {'/'.join(YELLOW + name + RESET for name in target2names[dep])}" if isinstance(dep, Target) \
                    else f" {str(dep)}"
            print(spec_str)

            if target.__doc__:
                # make indentation 4 spaces
                indent4 = unindent(target.__doc__).replace('\n', '\n    ')
                print(f"{GREY}{indent4}{RESET}")
            # print("=" * 80)
    return help


def default_clean(targets: Dict[str, Target]):
    @makes('clean')
    async def clean():
        print('Pymake help. Available targets:')
        await asyncio.gather(target.clean() for target in set(targets.values()))
    return clean
