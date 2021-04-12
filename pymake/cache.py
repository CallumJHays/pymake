from typing import Dict
import json

from .targets.wildcard import find_matching_target, NoTargetMatchError
from .targets.target import Target, FilePath
from .logging import logger


class TimestampCache(Dict[Target, float]):

    def __init__(self, path: FilePath, targets: Dict[str, Target]):
        self.path = path
        try:
            with open(path, 'r') as f:
                json_cache: Dict[str, float] = json.load(f)
                for name, data in json_cache.items():
                    try:
                        target = find_matching_target(name, targets)
                        assert target
                        self[target] = data
                    except NoTargetMatchError:
                        logger.debug(
                            f"target {name} is no longer defined in the PyMakefile. Discarding cache info.")
                logger.debug(
                    f"Loaded {len(self)} timestamps from cache file \"{path}\"")
        except FileNotFoundError:
            logger.debug(f"Cache file not found: \"{path}\"")

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
