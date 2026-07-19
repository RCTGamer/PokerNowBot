"""Unit tests for decision maker module."""

import pytest

from pokerbot_explainable.decision.heuristic.simple_heuristic import SimpleHeuristicDecisionMaker
from pokerbot_explainable.core.card_utils import Card, Suit, Rank
from pokerbot_explainable.core.game_engine.game_state import GameState
from pokerbot_explainable.core.constants.game import PlayerAction


def test_decision_maker_creation():
    """Test that we can create a decision maker."""
    dm = SimpleHeuristicDecisionMaker()
    assert dm.name == "SimpleHeuristic"


def test_preflop_hand_strength():
    """Test hand strength evaluation for preflop hands."""
    dm = SimpleHeuristicDecisionMaker()

    # Test pair of aces
    cards = [Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.HEARTS)]
    strength = dm._preflop_hand_strength(cards)
    assert strength > 0.8  # Should be strong

    # Test pair of twos
    cards = [Card(Rank.TWO, Suit.SPADES), Card(Rank.TWO, Suit.HEARTS)]
    strength = dm._preflop_hand_strength(cards)
    assert 0.3 <= strength <= 0.5  # Should be weak-medium

    # Test AK suited
    cards = [Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.SPADES)]
    strength = dm._preflop_hand_strength(cards)
    assert strength > 0.5  # Should be decent

    # Test 72 offsuit (worst hand)
    cards = [Card(Rank.SEVEN, Suit.CLUBS), Card(Rank.TWO, Suit.HEARTS)]
    strength = dm._preflop_hand_strength(cards)
    assert strength < 0.3  # Should be weak


def test_position_calculation():
    """Test position calculation relative to dealer."""
    dm = SimpleHeuristicDecisionMaker()

    # Test dealer position
    pos = dm._get_position(0, 0, 6)  # Player 0, dealer at 0, 6 players
    assert pos.name == "DEALER"  # Position.DEALER

    # Test small blind
    pos = dm._get_position(1, 0, 6)  # Player 1, dealer at 0
    assert pos.name == "SMALL_BLIND"  # Position.SMALL_BLIND

    # Test big blind
    pos = dm._get_position(2, 0, 6)  # Player 2, dealer at 0
    assert pos.name == "BIG_BLIND"  # Position.BIG_BLIND


def test_simple_decision_preflop():
    """Test simple decision making preflop."""
    dm = SimpleHeuristicDecisionMaker()

    # Create a simple game state
    game_state = GameState(num_players=2, starting_stack=100)
    player_id = 0

    # Give player a strong hand
    hole_cards = [Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.HEARTS)]

    # Make decision
    decision = dm.make_decision(game_state, player_id, hole_cards)

    # Check that we got a valid decision
    assert isinstance(decision.action, PlayerAction)
    assert 0 <= decision.amount <= 100  # Should not exceed stack
    assert 0.0 <= decision.confidence <= 1.0
    assert isinstance(decision.reasoning, str)
    assert len(decision.alternatives) <= 3  # Should limit alternatives


if __name__ == "__main__":
    pytest.main([__file__])