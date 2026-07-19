"""Decision making interface for pokerbot_explainable."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.game_engine.game_state import GameState
from ..core.card_utils import Card
from ..core.constants.game import PlayerAction


@dataclass
class Decision:
    """Represents a decision made by the AI with explanation.

    `factors` is an optional open-ended dict the bot can populate with the
    intermediate values considered behind its decision (hand strength,
    position, pot odds, equity, etc.). It exists to keep the bot's
    "chain of thought" inspectable without baking a specific schema into
    the abstract base. A plain human-readable `reasoning` string is still
    available for quick display.
    """
    action: PlayerAction
    amount: int  # Amount to bet/raise (if applicable)
    confidence: float  # Confidence in decision (0.0 to 1.0)
    reasoning: str  # Human-readable explanation of the decision
    alternatives: List[tuple[PlayerAction, int, str]]  # List of (action, amount, reason) alternatives considered
    factors: Dict[str, Any] = field(default_factory=dict)


class DecisionMaker(ABC):
    """Abstract base class for decision makers."""

    @abstractmethod
    def make_decision(self, game_state: GameState, player_id: int,
                     hole_cards: List[Card]) -> Decision:
        """
        Make a decision based on the current game state.

        Args:
            game_state: Current state of the game
            player_id: ID of the player making the decision
            hole_cards: The player's hole cards

        Returns:
            Decision object containing the chosen action and reasoning
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the decision maker.
        Returns:
            Name of the decision maker strategy
        """
        pass