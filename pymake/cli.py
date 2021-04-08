import click
from pathlib import Path
import importlib.util
from typing import Dict

from .targets.target import Target
from .targets.wildcard import find_matching_target
from .make import make


@click.command()
@click.argument("request", default="help")
@click.option("--makefile-path", "-m", default='PyMakefile.py')
@click.option("--cache-path", "-c", default='.pymake-cache')
@click.option("--n-workers", "-j", default=4)
def cli(
    request: str,
    makefile_path: str = 'PyMakefile.py',
    cache_path: str = '.pymake-cache',
    n_workers: int = 4
):
    "Run the makefile as a command-line app, handling arguments correctly"

    # TODO: handle being run from makefiles not named 'PyMakefile.py'
    # module = import_module(f".{makefile_path}", __name__)
    makefile = Path(makefile_path)
    spec = importlib.util.spec_from_file_location(
        makefile.stem, str(makefile_path))
    module = importlib.util.module_from_spec(spec)

    # collect all targets
    targets: Dict[str, Target] = {}
    for name in dir(module):
        export = getattr(module, name)
        if isinstance(export, Target):
            targets[name] = export

    try:
        target = getattr(module, request)
        assert isinstance(target, Target), \
            f"Expected requested target to be of class Target, but instead found {target.__class__}"

    except AttributeError:
        # no target was matched directly.
        # Perhaps this will match the output of a FileTarget?
        target = find_matching_target(request, targets)

    make(target, cache=cache_path, n_workers=n_workers)
