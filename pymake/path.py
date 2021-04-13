from pathlib import Path as _Path
import inspect
from .targets.target import FilePath, Target


class Path(_Path):

    def __new__(cls, path: FilePath):

        # make all paths relative to the source file of instantiation
        # by searching through the stack until not within definition of a
        # Target
        for frame in inspect.stack()[1:]:
            if not issubclass(frame.frame.f_locals.get('__class__', object), Target):
                srcdir = _Path(frame.filename).parent
                break
        else:
            raise Exception("bugger")
        return super().__new__(_Path, srcdir / path)
