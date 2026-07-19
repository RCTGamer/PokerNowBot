"""Game constants for pokerbot_explainable."""

from __future__ import annotations

from enum import Enum, auto
from typing import List


class GamePhase(Enum):
    """Phases of a poker hand."""
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()


class PlayerAction(Enum):
    """Possible actions a player can take."""
    FOLD = auto()
    CHECK = auto()
    CALL = auto()
    BET = auto()
    RAISE = auto()


class Position(Enum):
    """Player positions at the table (relative to dealer button)."""
    # These will be assigned dynamically based on dealer position
    DEALER = auto()      # Button
    SMALL_BLIND = auto() # SB
    BIG_BLIND = auto()   # BB
    EARLY = auto()       # Early position
    MIDDLE = auto()      # Middle position
    LATE = auto()        # Late position


# Default game configuration
DEFAULT_BLINDS = [1, 2]  # [small_blind, big_blind]
DEFAULT_STARTING_STACK = 100
DEFAULT_MAX_PLAYERS = 6