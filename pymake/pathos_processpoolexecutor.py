"""Main module."""
from multiprocessing.pool import MapResult
from typing import Any, Callable, Iterator, Optional, TypeVar
# monkey-patches multiprocessing so that pathos uses the superior serialization
import dill  # type: ignore
import multiprocess.pool  # type: ignore
from concurrent.futures import Future, ProcessPoolExecutor as _ProcessPoolExecutor

T = TypeVar('T')


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
        self.pool.apply_async(  # type: ignore
            fn, args, kwargs, callback=fut.set_result, error_callback=fut.set_exception)
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
