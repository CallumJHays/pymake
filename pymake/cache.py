from typing import Dict
import json
import logging

from .targets.wildcard import find_matching_target, NoTargetMatchError
from .targets.target import Target, FilePath


class Cache(Dict[Target, float]):

    def __init__(self, path: FilePath, targets: Dict[str, Target]):
        self.path = path
        with open(path, 'r') as f:
            json_cache: Dict[str, float] = json.load(f)
            for name, data in json_cache.items():
                try:
                    target = find_matching_target(name, targets)
                    self[target] = data
                except NoTargetMatchError:
                    logging.debug(
                        f"target {name} is no longer defined in the PyMakefile. Discarding cache info.")

    def save(self):
        with open(self.path, 'w') as f:
            json.dump({
                target.target: data
                for target, data in self.items()
            }, f)

    def __setitem__(self, k: Target, v: float):
        assert not k.has_wildcard(
        ), "Something went wrong with pymake. Wildcard targets should never be cached"
        assert k.do_cache, f"target {k} requested not to be cached."
        super().__setitem__(k, v)
        self.save()
