"""Scientific-state world builders."""

from scivaliditybench.states.absence import build_absence_world
from scivaliditybench.states.construct import build_construct_world
from scivaliditybench.states.disclosure import build_disclosure_world
from scivaliditybench.states.inferential import build_inferential_world
from scivaliditybench.states.relevance import build_relevance_world

STATE_BUILDERS = {
    "inferential": build_inferential_world,
    "blind": build_disclosure_world,
    "construct": build_construct_world,
    "absence": build_absence_world,
    "sunk_cost": build_relevance_world,
}

__all__ = ["STATE_BUILDERS"]
