from .cache import TimestampCache
from .cli import cli
from .decorator import makes
from .environment import env, PATH
from .shell import sh
from .make import make, make_sync
from .targets import Makefile, Target, Dependencies, Group
from pathlib import Path

__FLAG_IS_PYMAKEFILE__ = True

__all__ = ["TimestampCache", "cli", "makes", "env", "PATH", "Path",
           "sh", "make", "make_sync", "__FLAG_IS_PYMAKEFILE__",
           "Makefile", "Target", "Dependencies", "Group"]
