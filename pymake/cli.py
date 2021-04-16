import click
from runpy import run_path
from typing import Any, Dict, List
from pathlib import Path

from .targets.target import FilePath, Target, Union
from .targets.wildcard import NoTargetMatchError, find_matching_target
from .targets.clean import Clean
from .make import make_sync
from .logger import RED, logger, YELLOW, RESET, GREY
from .utils import unindent


class UserError(Exception):
    def __init__(self, msg: str, help: str, underlying: Exception):
        super().__init__(msg)
        self.msg = msg
        self.help = help
        self.__cause__ = underlying


def run(
    makefile: str,
    request: str,
    cache: str = '.pymake-cache',
    no_cache: bool = False,
    loglevel: Union[int, str] = "WARNING"
):
    try:
        logger.setLevel(loglevel)
        try:
            exports = run_path(makefile)
        except FileNotFoundError as e:
            raise UserError(
                f"Could not find makefile: \"{makefile}\".",
                "Please run from the correct directory or specify the path to the makefile with \"-m\".\n"
                "See help with \"pymake --help\" for more info.",
                e)

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
                if request == 'show-targets':
                    target = ShowTargets(targets)
                elif request == 'clean':
                    target = Clean(targets.values())
                else:
                    raise e

        make_sync(target, cache=None if no_cache else cache,
                  targets=targets, prefix_dir=Path(makefile).parent)

    except UserError as e:
        print(f"{RED}{e.msg}{RESET}\n{e.help}")


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
    @click.argument("request", default="show-targets")
    @click.option("--cache", default='.pymake-cache', help="Path to cache file")
    @click.option("--no-cache", default=False, help="Set to disable caching")
    def cmd(*args: Any, **kwargs: Any):
        run(*args, makefile=str(makefile),  # type: ignore
            loglevel=loglevel, **kwargs)  # type: ignore
    return cmd()


@click.command()
@click.argument("request", default="show-targets")
@click.option("--makefile", "-m", default='PyMakefile.py',
              help="Path to the makefile. Defaults to 'PyMakefile.py' in current directory.")
@click.option("--cache", default='.pymake-cache', help="Path to cache file")
@click.option("--no-cache", default=False, help="Set to disable caching")
@click.option("--loglevel", "-l", default='WARNING', help="loglevel for internal logs. Setting to 'DEBUG' may aid with debugging")
def cli_shell(*args: Any, **kwargs: Any):
    "Run the makefile as a command-line app, handling arguments correctly"
    run(*args, **kwargs)


class ShowTargets(Target):
    "Display this target help information"

    def __init__(self, targets: Dict[str, Target]):
        super().__init__(None, [])
        self.targets = targets

    async def make(self):
        target2names: Dict[Target, List[str]] = {}
        for name, target in self.targets.items():
            target2names.setdefault(target, []).append(name)

        def print_target(target: Target, names: List[str]):
            spec_str = f"    - {'/'.join(f'{YELLOW}{name}{RESET}' for name in names)} {repr(target)}"
            spec_str += ':'
            for dep in target.deps:
                spec_str += f" {'/'.join(YELLOW + name + RESET for name in target2names[dep])}" if isinstance(dep, Target) \
                    else f" {str(dep)}"
            print(spec_str)

            if target.__doc__:
                spaces = ' ' * 10
                indent4 = f'{spaces}{unindent(target.__doc__)}' \
                    .replace('\n', f'\n{spaces}')
                print(f"{GREY}{indent4}{RESET}")

        print('All Targets:')
        for target, names in target2names.items():
            print_target(target, names)

        print_target(self, ['show-targets'])
        clean_all = Clean(target2names.keys())
        clean_all.__doc__ = "Clean all targets by deleting all specified target files"
        print_target(clean_all, ['clean'])
        print(f'{GREY}For help with the pymake cli, run "pymake --help"')
