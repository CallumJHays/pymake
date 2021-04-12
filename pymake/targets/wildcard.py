from typing import Set, Dict
from .target import FilePath, Target

match_cache: Dict[str, Target] = {}


def find_matching_target(request: FilePath, targets: Dict[str, Target]) -> Target:
    matching: Set[Target] = set()
    checked: Set[Target] = set()

    req_str = str(request)
    if req_str in match_cache:
        return match_cache[req_str]
    elif req_str in targets:
        return targets[req_str]

    for target in targets.values():
        if not target in checked:
            if target.matches(req_str):
                if any(matching):
                    raise MultipleTargetsMatchError(
                        f"Multiple target match the request '{req_str}': {matching.pop()} & {target}"
                    )

                matching.add(target)

            checked.add(target)

    if not any(matching):
        # TODO: levenshtein debugging assistance
        raise NoTargetMatchError(
            f"No target matches the request '{req_str}'")

    match_cache[req_str] = found = matching.pop()
    return found


class NoTargetMatchError(Exception):
    pass


class MultipleTargetsMatchError(Exception):
    pass

# def _levenshtein_distance(token1: str, token2: str) -> float:
#     "Returns a scalar representing a 'difference score' between two strings"
#     # ripped from https://blog.paperspace.com/implementing-levenshtein-distance-word-autocomplete-autocorrect/

#     distances = [[0] * (len(token2) + 1)] * (len(token1) + 1)

#     for t1 in range(len(token1) + 1):
#         distances[t1][0] = t1

#     for t2 in range(len(token2) + 1):
#         distances[0][t2] = t2

#     a = 0
#     b = 0
#     c = 0

#     for t1 in range(1, len(token1) + 1):
#         for t2 in range(1, len(token2) + 1):
#             if (token1[t1-1] == token2[t2-1]):
#                 distances[t1][t2] = distances[t1 - 1][t2 - 1]
#             else:
#                 a = distances[t1][t2 - 1]
#                 b = distances[t1 - 1][t2]
#                 c = distances[t1 - 1][t2 - 1]

#                 if (a <= b and a <= c):
#                     distances[t1][t2] = a + 1
#                 elif (b <= a and b <= c):
#                     distances[t1][t2] = b + 1
#                 else:
#                     distances[t1][t2] = c + 1

#     return distances[len(token1)][len(token2)]
