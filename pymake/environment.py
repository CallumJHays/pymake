import contextlib
import os
import multiprocessing

N_CPU_CORES = multiprocessing.cpu_count()
PATH = os.getenv('PATH')


@contextlib.contextmanager
def env_vars(isolated: bool = False, **vars: str):
    global PATH
    before = os.environ.copy()
    before_PATH = os.environ.get('PATH')
    if isolated:
        os.environ.clear()
    os.environ.update(vars)
    PATH = os.environ.get('PATH')  # type: ignore

    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(before)
        PATH = before_PATH  # type: ignore
