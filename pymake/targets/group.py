from .target import Target, Dependencies


class Group(Target):

    def __init__(self, deps: Dependencies, do_cache: bool = False):
        super().__init__(None, deps, do_cache=do_cache)

    async def make(self):
        pass
