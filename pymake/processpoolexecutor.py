"""Main module."""
import pickle
from multiprocessing.pool import MapResult
from typing import Any, Callable, Optional, TypeVar, Iterator, Union
# monkey-patches multiprocessing so that pathos uses the superior serialization
import dill  # type: ignore
import multiprocess.pool  # type: ignore
from types import TracebackType

from concurrent.futures import Future, ProcessPoolExecutor as _ProcessPoolExecutor
# monkey-patches pickle so that pathos uses the superior serialization
from tblib import pickling_support  # type: ignore
pickling_support.install()  # type: ignore
T = TypeVar('T')


class ExceptionWithTraceback:
    def __init__(self, exc: Exception, tb: TracebackType):
        self.exception = exc
        self.tb_dump = pickle.dumps(tb)

    def __reduce__(self):
        def inner(exc: Exception, tb: bytes):
            return exc.with_traceback(pickle.loads(tb))
        return inner, (self.exception, self.tb_dump)


multiprocess.pool.ExceptionWithTraceback = ExceptionWithTraceback

# SerializableStack = List[Tuple[int, int]]


# def create_selftracingerror(original: BaseException, traceback: TracebackType):
#     stack: SerializableStack = []

#     frame = traceback.tb_frame
#     stack.append((frame.f_lasti, frame.f_lineno))

#     while traceback.tb_next:
#         frame = traceback.tb_frame
#         stack.append((frame.f_lasti, frame.f_lineno))
#         traceback = traceback.tb_next

#     return _SelfTracingError(original, stack)


# class _SelfTracingError(Exception):

#     def __init__(self, original: BaseException = None, stack: SerializableStack = None):
#         super().__init__()
#         self.original = original
#         self.stack = stack

#     def recreate(self):
#         traceback = None
#         frame = inspect.stack()[0].frame
#         for f_lasti, f_lineno in self.stack:
#             traceback = TracebackType(
#                 traceback, frame, f_lasti, f_lineno)
#         res = self.original.with_traceback(traceback)
#         return res


class ProcessPoolExecutor(_ProcessPoolExecutor):

    def __init__(self, max_workers: Optional[int] = None):
        kwargs = {'nodes': max_workers} if max_workers else {}
        self.pool = multiprocess.pool.Pool(**kwargs)

    def submit(
        self,
        fn: Callable[..., T],
        *args: Any,
        **kwargs: Any
    ) -> 'Future[T]':
        fut: 'Future[T]' = Future()

        def reraise(e: Exception):
            raise e

        self.pool.apply_async(  # type: ignore
            fn, args, kwargs, callback=fut.set_result, error_callback=reraise)
        fut.set_running_or_notify_cancel()
        return fut

    def map(
        self,
        fn: Callable[..., T],
        *iterables: Any,
        timeout: Optional[float] = None,
        chunksize: int = 1
    ) -> Iterator[T]:
        res: MapResult[T] = \
            self.pool.map_async(  # type: ignore
                fn, iterables, chunksize=chunksize)
        return iter(res.get(timeout))

    def shutdown(self, wait: bool = True):
        self.pool.close()
        if wait:
            self.pool.join()
        self.pool.terminate()
