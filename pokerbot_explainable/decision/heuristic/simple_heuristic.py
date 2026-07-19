"""Simple heuristic decision maker for pokerbot_explainable."""

from __future__ import annotations

import random
from typing import List

from ...core.game_engine.game_state import GameState
from ...core.card_utils import Card, Suit, Rank
from ...core.constants.game import PlayerAction, Position
from ...core.hand_evaluator import HandEvaluator
from ..base import Decision, DecisionMaker


class SimpleHeuristicDecisionMaker(DecisionMaker):
    """
    Simple heuristic decision maker that makes decisions based on:
    - Hand strength (using hand rankings)
    - Position at table
    - Pot odds
    - Stack size
    - Number of opponents
    """

    def __init__(self, name: str = "SimpleHeuristic"):
        self.name = name

    def get_name(self) -> str:
        """
        Get the name of the decision maker.
        Returns:
            Name of the decision maker strategy
        """
        return self.name

    def make_decision(self, game_state: GameState, player_id: int,
                     hole_cards: List[Card]) -> Decision:
        """
        Make a decision based on simple heuristics.

        Args:
            game_state: Current state of the game
            player_id: ID of the player making the decision
            hole_cards: The player's hole cards

        Returns:
            Decision object with action, amount, confidence, reasoning,
            alternatives, and a `factors` dict describing the inputs the
            heuristic consulted (hand strength, position, pot odds, etc.).
        """
        player_state = game_state.players[player_id]

        # Calculate position relative to dealer
        position = self._get_position(player_id, game_state.dealer_position, game_state.num_players)

        # Estimate hand strength (simplified)
        hand_strength = self._estimate_hand_strength(hole_cards, game_state.board_cards)

        # Calculate pot odds
        pot_odds = self._calculate_pot_odds(game_state, player_id)

        # Determine action based on heuristics
        action, amount, confidence, reasoning = self._apply_heuristics(
            game_state, player_id, hole_cards, hand_strength, position, pot_odds
        )

        # Generate alternatives considered
        alternatives = self._generate_alternatives(
            game_state, player_id, hole_cards, hand_strength, position, pot_odds, action, amount
        )

        # Capture the intermediate inputs that drove this decision so the
        # caller (or a future logger) can inspect the bot's chain of
        # thought without re-implementing the heuristic.
        factors = self._compute_factors(
            game_state, player_id, hole_cards, hand_strength, position, pot_odds
        )

        return Decision(
            action=action,
            amount=amount,
            confidence=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
            factors=factors,
        )

    def _get_position(self, player_id: int, dealer_position: int, num_players: int) -> Position:
        """Get position relative to dealer button."""
        pos = (player_id - dealer_position) % num_players

        if pos == 0:
            return Position.DEALER
        elif pos == 1:
            return Position.SMALL_BLIND
        elif pos == 2:
            return Position.BIG_BLIND
        elif pos < num_players // 3:
            return Position.EARLY
        elif pos < 2 * num_players // 3:
            return Position.MIDDLE
        else:
            return Position.LATE

    def _estimate_hand_strength(self, hole_cards: List[Card], board_cards: List[Card]) -> float:
        """
        Estimate hand strength on a scale of 0-1.
        This is a simplified version - in a real implementation we'd use the hand evaluator.
        """
        if len(board_cards) == 0:  # Preflop
            return self._preflop_hand_strength(hole_cards)
        else:  # Postflop
            # Use the HandEvaluator to get actual hand rank and class
            evaluator = HandEvaluator()
            rank, hand_class = evaluator.evaluate_hand(board_cards, hole_cards)
            # treys rank: lower is better, best possible is 1, worst is ~7462
            # Convert to 0-1 scale where 1 is best
            MAX_RANK = 7462
            strength = 1.0 - (rank / MAX_RANK)
            return max(0.0, min(1.0, strength))

    def _preflop_hand_strength(self, hole_cards: List[Card]) -> float:
        """Estimate preflop hand strength."""
        card1, card2 = hole_cards

        # Check for pair
        if card1.rank == card2.rank:
            # Pairs: AA-TT are strong, 99-22 are medium
            rank_value = card1.rank.value  # Assuming Rank enum has values 2-14
            if rank_value >= 10:  # AA, KK, QQ, JJ, TT
                return 0.8 + (rank_value - 10) * 0.04  # 0.8-1.0
            elif rank_value >= 7:  # 99-77
                return 0.5 + (rank_value - 7) * 0.1   # 0.5-0.8
            else:  # 66-22
                return 0.3 + (rank_value - 2) * 0.04  # 0.3-0.5

        # Check for suited
        suited = card1.suit == card2.suit

        # Check for connectedness
        rank_diff = abs(card1.rank.value - card2.rank.value)

        # High cards
        high_card_points = max(card1.rank.value, card2.rank.value)
        avg_card_points = (card1.rank.value + card2.rank.value) / 2

        # Base score
        score = 0.0

        # High card strength
        if high_card_points >= 14:  # Ace
            score += 0.3
        elif high_card_points >= 13:  # King
            score += 0.25
        elif high_card_points >= 12:  # Queen
            score += 0.2
        elif high_card_points >= 11:  # Jack
            score += 0.15
        elif high_card_points >= 10:  # Ten
            score += 0.1

        # Second card kicker
        if high_card_points >= 10:  # If we have a high card
            if card2.rank.value >= 10:  # Both high cards
                score += 0.15
            elif card2.rank.value >= 8:  # Good kicker
                score += 0.1
            elif card2.rank.value >= 6:  # Decent kicker
                score += 0.05

        # Suited bonus
        if suited:
            score += 0.15

        # Connected bonus
        if rank_diff == 1:
            score += 0.15  # Connectors
        elif rank_diff == 2:
            score += 0.1   # One-gap
        elif rank_diff == 3:
            score += 0.05  # Two-gap

        # Pair bonus already handled above

        # Cap at 1.0
        return min(score, 1.0)

    def _calculate_pot_odds(self, game_state: GameState, player_id: int) -> float:
        """Calculate pot odds as a ratio."""
        player_state = game_state.players[player_id]
        to_call = game_state.current_bet - player_state['bet_this_round']

        if to_call <= 0:
            return float('inf')  # Free to call/check

        pot_size = game_state.pot
        return pot_size / to_call if to_call > 0 else float('inf')

    def _apply_heuristics(self, game_state: GameState, player_id: int,
                         hole_cards: List[Card], hand_strength: float,
                         position: Position, pot_odds: float) -> tuple:
        """Apply heuristic rules to determine action."""
        player_state = game_state.players[player_id]
        to_call = game_state.current_bet - player_state['bet_this_round']

        # Default to fold
        action = PlayerAction.FOLD
        amount = 0
        confidence = 0.5
        reasoning = "Default fold with weak hand"

        # Adjust thresholds based on position
        position_bonus = {
            Position.EARLY: -0.1,
            Position.MIDDLE: 0.0,
            Position.LATE: 0.1,
            Position.SMALL_BLIND: -0.05,
            Position.BIG_BLIND: 0.0,
            Position.DEALER: 0.15
        }.get(position, 0.0)

        adjusted_strength = hand_strength + position_bonus

        # Preflop logic (no board cards)
        if len(game_state.board_cards) == 0:
            # Premium hands
            if adjusted_strength >= 0.8:
                if to_call == 0:
                    action = PlayerAction.BET
                    amount = max(game_state.blinds[1] * 3, game_state.current_bet * 3)
                    confidence = 0.9
                    reasoning = f"Premium hand (strength: {adjusted_strength:.2f}) raising for value"
                else:
                    # We're facing a bet
                    if pot_odds > 2.0 or adjusted_strength > 0.85:
                        action = PlayerAction.CALL
                        amount = to_call
                        confidence = 0.8
                        reasoning = f"Premium hand getting good odds ({pot_odds:.1f}:1)"
                    else:
                        # Re-raise
                        action = PlayerAction.RAISE
                        amount = max(game_state.current_bet * 3, game_state.blinds[1] * 4)
                        confidence = 0.85
                        reasoning = f"Premium hand re-raising for value"

            # Strong hands
            elif adjusted_strength >= 0.6:
                if to_call == 0:
                    action = PlayerAction.CHECK
                    amount = 0
                    confidence = 0.7
                    reasoning = f"Strong hand (strength: {adjusted_strength:.2f}) seeing flop"
                elif pot_odds > 3.0:
                    action = PlayerAction.CALL
                    amount = to_call
                    confidence = 0.75
                    reasoning = f"Strong hand getting excellent odds ({pot_odds:.1f}:1)"
                elif to_call <= game_state.blinds[1] * 2:
                    action = PlayerAction.CALL
                    amount = to_call
                    confidence = 0.6
                    reasoning = f"Decent hand calling small bet"
                else:
                    action = PlayerAction.FOLD
                    confidence = 0.6
                    reasoning = f"Strong hand but bet too large for pot odds"

            # Playable hands
            elif adjusted_strength >= 0.4:
                if to_call == 0:
                    action = PlayerAction.CHECK
                    amount = 0
                    confidence = 0.6
                    reasoning = f"Playable hand (strength: {adjusted_strength:.2f}) seeing flop"
                elif pot_odds > 5.0:
                    action = PlayerAction.CALL
                    amount = to_call
                    confidence = 0.65
                    reasoning = f"Playable hand getting great odds ({pot_odds:.1f}:1)"
                elif to_call <= game_state.blinds[1]:
                    action = PlayerAction.CALL
                    amount = to_call
                    confidence = 0.55
                    reasoning = f"Marginal hand calling minimum bet"
                else:
                    action = PlayerAction.FOLD
                    confidence = 0.6
                    reasoning = f"Marginal hand folding to larger bet"

            # Weak hands
            else:
                if to_call == 0:
                    action = PlayerAction.CHECK
                    amount = 0
                    confidence = 0.5
                    reasoning = f"Weak hand (strength: {adjusted_strength:.2f}) seeing flop for free"
                elif to_call <= game_state.blinds[1] // 2 and position in [Position.LATE, Position.DEALER]:
                    action = PlayerAction.CALL
                    amount = to_call
                    confidence = 0.4
                    reasoning = f"Weak hand seeing cheap flop in position"
                else:
                    action = PlayerAction.FOLD
                    confidence = 0.5
                    reasoning = f"Weak hand folding preflop"

        # Postflop logic (simplified)
        else:
            # Made hand or draw
            if adjusted_strength >= 0.7:  # Strong made hand
                if to_call == 0:
                    action = PlayerAction.BET
                    amount = max(game_state.pot // 2, game_state.big_blind)
                    confidence = 0.8
                    reasoning = f"Strong made hand betting for value"
                else:
                    if pot_odds > 2.0:
                        action = PlayerAction.CALL
                        amount = to_call
                        confidence = 0.75
                        reasoning = f"Strong hand getting good pot odds"
                    else:
                        action = PlayerAction.RAISE
                        amount = max(game_state.current_bet * 2, game_state.pot // 2)
                        confidence = 0.8
                        reasoning = f"Strong hand raising for value"

            elif adjusted_strength >= 0.5:  # Medium hand or good draw
                if to_call == 0:
                    action = PlayerAction.CHECK
                    amount = 0
                    confidence = 0.6
                    reasoning = f"Medium hand or draw seeing next card"
                elif pot_odds > 4.0:
                    action = PlayerAction.CALL
                    amount = to_call
                    confidence = 0.7
                    reasoning = f"Getting excellent odds for draw/medium hand"
                elif to_call <= game_state.pot // 3:
                    action = PlayerAction.CALL
                    amount = to_call
                    confidence = 0.6
                    reasoning = f"Calling reasonable bet with medium hand"
                else:
                    action = PlayerAction.FOLD
                    confidence = 0.6
                    reasoning = f"Bet too large for hand strength"

            else:  # Weak hand or air
                if to_call == 0:
                    action = PlayerAction.CHECK
                    amount = 0
                    confidence = 0.5
                    reasoning = f"Weak hand giving up"
                elif to_call <= game_state.big_blind and position in [Position.LATE, Position.DEALER]:
                    # Occasional float/bluff
                    if random.random() < 0.2:  # 20% chance to float
                        action = PlayerAction.CALL
                        amount = to_call
                        confidence = 0.4
                        reasoning = f"Occasional float in position"
                    else:
                        action = PlayerAction.FOLD
                        confidence = 0.6
                        reasoning = f"Weak hand folding"
                else:
                    action = PlayerAction.FOLD
                    confidence = 0.6
                    reasoning = f"Weak hand folding to bet"

        # Ensure amount doesn't exceed stack
        if action in [PlayerAction.BET, PlayerAction.RAISE, PlayerAction.CALL]:
            amount = min(amount, player_state['stack'])
            if amount <= 0:
                action = PlayerAction.FOLD
                amount = 0
                confidence = 0.5
                reasoning = "Insufficient chips to continue"

        return action, amount, confidence, reasoning

    def _generate_alternatives(self, game_state: GameState, player_id: int,
                              hole_cards: List[Card], hand_strength: float,
                              position: Position, pot_odds: float,
                              chosen_action: PlayerAction, chosen_amount: int) -> list:
        """Generate alternative actions that were considered."""
        alternatives = []
        player_state = game_state.players[player_id]
        to_call = game_state.current_bet - player_state['bet_this_round']

        # Consider folding
        if chosen_action != PlayerAction.FOLD:
            alternatives.append((
                PlayerAction.FOLD,
                0,
                "Fold to conserve chips with marginal hand"
            ))

        # Consider checking/calling
        if to_call >= 0 and chosen_action not in [PlayerAction.CHECK, PlayerAction.CALL]:
            if to_call == 0:
                alternatives.append((
                    PlayerAction.CHECK,
                    0,
                    "Check to see next card for free"
                ))
            else:
                alternatives.append((
                    PlayerAction.CALL,
                    to_call,
                    f"Call {to_call} to see next card"
                ))

        # Consider betting/raising with different sizes
        if player_state['stack'] > 0 and chosen_action not in [PlayerAction.BET, PlayerAction.RAISE]:
            big_blind = game_state.blinds[1]
            # Small bet
            if game_state.current_bet == 0:  # No bet yet
                small_bet = max(big_blind, game_state.pot // 3)
                if 0 < small_bet <= player_state['stack']:
                    alternatives.append((
                        PlayerAction.BET,
                        small_bet,
                        f"Bet {small_bet} for value or protection"
                    ))
            else:  # Facing a bet, consider raising
                big_blind = game_state.blinds[1]
                min_raise = game_state.current_bet + big_blind
                if min_raise <= player_state['stack'] + player_state['bet_this_round']:
                    alternatives.append((
                        PlayerAction.RAISE,
                        min_raise,
                        f"Raise to {min_raise} for value or as bluff"
                    ))

        # Consider all-in
        if player_state['stack'] > 0 and player_state['stack'] != chosen_amount:
            if chosen_action in [PlayerAction.BET, PlayerAction.RAISE, PlayerAction.CALL]:
                alternatives.append((
                    PlayerAction.BET,  # All-in is just betting all your chips
                    player_state['stack'],
                    "All-in for maximum pressure or value"
                ))

        # Limit to 3 alternatives
        return alternatives[:3]

    def _compute_factors(self, game_state: GameState, player_id: int,
                        hole_cards: List[Card], hand_strength: float,
                        position: Position, pot_odds: float) -> dict:
        """Capture the heuristic's inputs as a structured factors dict.

        Pure data extraction — no new math, just the values that
        `_apply_heuristics` already consulted. Aimed at keeping the bot's
        reasoning inspectable from outside (debugger / future logger)
        without leaking private state.
        """
        player_state = game_state.players[player_id]
        to_call = game_state.current_bet - player_state['bet_this_round']
        stack = player_state['stack']
        spr = (stack / game_state.pot) if game_state.pot > 0 else float('inf')

        return {
            "hand_strength": round(hand_strength, 4),
            "position": position.name,
            "pot_odds": (round(pot_odds, 4) if pot_odds != float('inf') else "infinity"),
            "to_call": to_call,
            "stack": stack,
            "pot": game_state.pot,
            "stack_to_pot_ratio": (round(spr, 4) if spr != float('inf') else "infinity"),
            "phase": game_state.phase.name,
            "board_card_count": len(game_state.board_cards),
        }