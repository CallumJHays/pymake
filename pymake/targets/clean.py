
import asyncio
from typing import Iterable, TYPE_CHECKING
from .target import Target
if TYPE_CHECKING:
    from ..cache import TimestampCache

class Clean(Target):
    def __init__(self, targets: Iterable[Target]):
        super().__init__(None, [])
        self.targets = targets
    
    async def make(self, cache: 'TimestampCache'): # type: ignore
        await asyncio.gather(*(target.clean(cache) for target in self.targets))
