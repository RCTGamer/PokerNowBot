"""Top-level hand harness.

`play_one_hand` is the glue between the game engine and the bot. It runs
the engine forward, asks each player's `DecisionMaker` for an action at
the appropriate turn, applies the action via `GameState.take_action`,
and accumulates a per-action trace so the bot's reasoning can be
inspected or replayed later. The trace is a plain `list[dict]` (one dict
per action) — no logger or sink here; that lives behind the
`explainability/` package once we know what to actually log.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from .core.game_engine.game_state import GameState
from .decision.base import DecisionMaker


def play_one_hand(
    deciders: Sequence[DecisionMaker],
    num_players: int = 2,
    **game_kwargs: Any,
) -> Tuple[List[int], List[Dict[str, Any]]]:
    """Play one hand to completion and return `(winners, trace)`.

    Args:
        deciders: One `DecisionMaker` per player, indexed by player id.
                  `len(deciders)` must equal `num_players`.
        num_players: Number of players at the table.
        **game_kwargs: Forwarded to `GameState(num_players=..., ...)` so
                       callers can pin starting stack, blinds, dealer, etc.

    Returns:
        winners: Player id(s) who won the pot.
        trace:   One dict per action taken:
                     {
                       "player_id": int,
                       "phase": str,
                       "action": str,
                       "amount": int,
                       "confidence": float,
                       "reasoning": str,
                       "alternatives": [(action, amount, reason), ...],
                       "factors": {...},
                       "snapshot": {...}  # GameState snapshot AFTER the action
                     }
    """
    if len(deciders) != num_players:
        raise ValueError(
            f"Need one DecisionMaker per player ({num_players}), got {len(deciders)}"
        )

    gs = GameState(num_players=num_players, **game_kwargs)
    trace: List[Dict[str, Any]] = []

    # Drive the hand forward. The engine auto-advances streets when no
    # player can act (all-in/folded), so the only manual calls we make
    # are for active players' turns.
    while not gs.is_hand_complete():
        player_id = gs.current_player

        # Bot decides.
        decision = deciders[player_id].make_decision(
            gs,
            player_id,
            gs.players[player_id]['hole_cards'],
        )

        # Apply action. The bot's `amount` is the literal additional chips
        # for CALL, or the **total bet to put out** for BET/RAISE — matching
        # the engine's take_action contract.
        applied = gs.take_action(player_id, decision.action, decision.amount)
        if not applied:
            # Bot produced an invalid action for this state (e.g. CHECK
            # when there's a bet). Surface it rather than silently looping —
            # any caller's regression test will catch regressions here.
            raise RuntimeError(
                f"DecisionMaker for player {player_id} produced an invalid "
                f"action: {decision.action!s} {decision.amount} in phase {gs.phase.name}"
            )

        trace.append(_trace_entry(player_id, gs, _decision_to_dict(decision)))

    return gs.get_winners(), trace


# -------------------------------------------------------------------------
# Trace serialization helpers
# -------------------------------------------------------------------------
def _decision_to_dict(decision: Any) -> Dict[str, Any]:
    """Flatten a Decision into a JSON-friendly dict (no enum values)."""
    return {
        "action": decision.action.name,
        "amount": decision.amount,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning,
        "alternatives": [
            (a.name, amt, reason) for (a, amt, reason) in decision.alternatives
        ],
        "factors": dict(decision.factors),
    }


def _trace_entry(player_id: int, gs: GameState, decision_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Build the per-action trace entry returned from `play_one_hand`."""
    return {
        "player_id": player_id,
        "phase": gs.phase.name,
        "action": decision_dict["action"],
        "amount": decision_dict["amount"],
        "confidence": decision_dict["confidence"],
        "reasoning": decision_dict["reasoning"],
        "alternatives": decision_dict["alternatives"],
        "factors": decision_dict["factors"],
        "snapshot": gs.get_game_state_snapshot(),
    }
