import contextlib
import os
import multiprocessing
from typing import Dict

N_CPU_CORES = multiprocessing.cpu_count()
PATH = os.getenv('PATH')

@contextlib.contextmanager
def env_isolated(**vars: str):
    with _env_inner(True, vars):
        yield

@contextlib.contextmanager
def env(**vars: str):
    with _env_inner(False, vars):
        yield

@contextlib.contextmanager
def _env_inner(isolated: bool, vars: Dict[str, str]):
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