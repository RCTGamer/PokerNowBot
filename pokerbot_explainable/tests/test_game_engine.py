"""Unit tests for game_engine module."""

import pytest

from pokerbot_explainable.core.game_engine.game_state import GameState, PlayerState
from pokerbot_explainable.core.card_utils import Card, Suit, Rank
from pokerbot_explainable.core.constants.game import GamePhase, PlayerAction


def test_game_state_initialization():
    """Test that a new game state is initialized correctly."""
    gs = GameState(num_players=2)

    assert gs.num_players == 2
    assert gs.phase == GamePhase.PREFLOP
    assert gs.pot == 3  # Small blind (1) + Big blind (2)
    assert gs.current_bet == 2  # Big blind amount
    assert len(gs.board_cards) == 0  # No community cards yet
    assert len(gs.players) == 2

    # Check initial player states
    assert gs.players[0]['stack'] == 99  # SB posted 1
    assert gs.players[0]['bet_this_round'] == 1
    assert gs.players[1]['stack'] == 98  # BB posted 2
    assert gs.players[1]['bet_this_round'] == 2

    # Check that dealer position is correct
    assert gs.dealer_position == 0
    # For heads-up (2 players): dealer is SB (player 0), next player is BB (player 1)
    assert gs.small_blind_index == 0  # Dealer is SB in heads-up
    assert gs.big_blind_index == 1    # Non-dealer is BB in heads-up


def test_game_state_initialization_6_players():
    """Test that a new game state with 6 players is initialized correctly."""
    gs = GameState(num_players=6)

    assert gs.num_players == 6
    assert gs.phase == GamePhase.PREFLOP
    assert gs.pot == 3  # Small blind (1) + Big blind (2)
    assert gs.current_bet == 2  # Big blind amount
    assert len(gs.board_cards) == 0
    assert len(gs.players) == 6

    # Check blind positions
    assert gs.dealer_position == 0
    assert gs.small_blind_index == 1
    assert gs.big_blind_index == 2

    # Check blinds were posted correctly
    assert gs.players[1]['bet_this_round'] == 1  # SB
    assert gs.players[2]['bet_this_round'] == 2  # BB


def test_player_actions_fold():
    """Test that a player can fold correctly."""
    gs = GameState(num_players=2)
    initial_stack_p0 = gs.players[0]['stack']

    # Player 0 (first to act after BB) folds
    result = gs.take_action(0, PlayerAction.FOLD)
    assert result == True

    # Check player state
    assert gs.players[0]['is_active'] == False
    assert gs.players[0]['stack'] == initial_stack_p0  # Shouldn't change when folding

    # Check game state
    assert gs.pot == 3  # Still just the blinds
    assert gs.current_bet == 2  # Still BB amount to call


def test_player_actions_check():
    """Test that a player can check when there's no bet."""
    gs = GameState(num_players=2)
    # Skip to a state where we can check
    # First, have player 0 call the blind
    gs.take_action(0, PlayerAction.CALL, 2)  # Call the BB of 2

    # Now it should be player 1's turn (the BB) and they should be able to check
    assert gs.current_player == 1
    assert gs.current_bet == 2
    assert gs.players[1]['bet_this_round'] == 2  # BB already posted 2

    # Player 1 checks
    result = gs.take_action(1, PlayerAction.CHECK)
    assert result == True

    # Check player state
    assert gs.players[1]['bet_this_round'] == 2  # Should still be 2
    assert gs.players[1]['is_all_in'] == False

    # Betting round should be complete now
    assert gs.betting_round_complete == True
    assert gs.phase == GamePhase.FLOP  # Should have advanced to flop
    assert len(gs.board_cards) == 3  # Flop should be dealt


def test_player_actions_call():
    """Test that a player can call correctly."""
    gs = GameState(num_players=2)
    initial_stack_p0 = gs.players[0]['stack']
    initial_stack_p1 = gs.players[1]['stack']

    # Player 0 calls the big blind
    result = gs.take_action(0, PlayerAction.CALL, 2)
    assert result == True

    # Check player 0 state
    assert gs.players[0]['stack'] == initial_stack_p0 - 2
    assert gs.players[0]['bet_this_round'] == 2
    assert gs.players[0]['is_all_in'] == False

    # Check pot and bet amounts
    # Pot = 3 (initial blinds: SB 1 + BB 2) + 2 (chips SB paid to call) = 5
    assert gs.pot == 5
    assert gs.current_bet == 2

    # Now player 1 (BB) can check
    gs.take_action(1, PlayerAction.CHECK)
    assert gs.betting_round_complete == True
    assert gs.phase == GamePhase.FLOP


def test_player_actions_bet():
    """Test that a player can bet/raise correctly."""
    gs = GameState(num_players=2)

    # Player 0 calls the BB first
    gs.take_action(0, PlayerAction.CALL, 2)

    # Now player 1 (BB) bets
    initial_stack_p1 = gs.players[1]['stack']
    result = gs.take_action(1, PlayerAction.BET, 5)  # Bet 5 total
    assert result == True

    # Check player 1 state
    assert gs.players[1]['stack'] == initial_stack_p1 - 3  # Already had 2 in, needs 3 more
    assert gs.players[1]['bet_this_round'] == 5
    assert gs.current_bet == 5
    assert gs.pot == 3 + 2 + 3  # Blinds + call + additional chips for bet

    # Now player 0 needs to call the raise (5-2 = 3 additional to match)
    assert gs.current_player == 0
    gs.take_action(0, PlayerAction.CALL, 3)  # Pay 3 more to match the bet of 5

    # Check player 0 state after calling
    assert gs.players[0]['bet_this_round'] == 5
    assert gs.players[0]['stack'] == 99 - 2 - 3  # Initial - SB call amount - additional to reach 5

    # Betting round should be complete
    assert gs.betting_round_complete == True
    assert gs.phase == GamePhase.FLOP


def test_player_actions_all_in():
    """Test that a player can go all-in correctly."""
    gs = GameState(num_players=2, starting_stack=5)  # Small stack for testing

    # Player 0 goes all-in
    result = gs.take_action(0, PlayerAction.BET, 5)  # All in
    assert result == True

    # Check player 0 state
    assert gs.players[0]['stack'] == 0
    assert gs.players[0]['is_all_in'] == True
    assert gs.players[0]['bet_this_round'] == 5
    assert gs.current_bet == 5

    # Player 1 should be able to call all-in
    assert gs.current_player == 1
    initial_stack_p1 = gs.players[1]['stack']
    result = gs.take_action(1, PlayerAction.CALL, 5)  # Call all-in
    assert result == True

    # Check player 1 state
    assert gs.players[1]['stack'] == initial_stack_p1 - 5
    assert gs.players[1]['is_all_in'] == True
    assert gs.players[1]['bet_this_round'] == 5

    # Betting round should be complete
    assert gs.betting_round_complete == True
    assert gs.phase == GamePhase.FLOP


def test_game_progression_through_streets():
    """Test that the game progresses through all streets correctly."""
    gs = GameState(num_players=2)

    # Start at preflop
    assert gs.phase == GamePhase.PREFLOP
    assert len(gs.board_cards) == 0

    # Complete preflop betting (both check/call)
    gs.take_action(0, PlayerAction.CALL, 2)  # BB
    gs.take_action(1, PlayerAction.CHECK)    # SB checks

    # Should now be at flop
    assert gs.phase == GamePhase.FLOP
    assert len(gs.board_cards) == 3

    # Complete flop betting
    gs.take_action(0, PlayerAction.CHECK)
    gs.take_action(1, PlayerAction.CHECK)

    # Should now be at turn
    assert gs.phase == GamePhase.TURN
    assert len(gs.board_cards) == 4

    # Complete turn betting
    gs.take_action(0, PlayerAction.CHECK)
    gs.take_action(1, PlayerAction.CHECK)

    # Should now be at river
    assert gs.phase == GamePhase.RIVER
    assert len(gs.board_cards) == 5

    # Complete river betting
    gs.take_action(0, PlayerAction.CHECK)
    gs.take_action(1, PlayerAction.CHECK)

    # Should now be at showdown
    assert gs.phase == GamePhase.SHOWDOWN


def test_showdown_winner_determination():
    """Test that the winner is correctly determined at showdown."""
    # Let's do a proper test by playing through a hand
    gs_test = GameState(num_players=2)

    # Both players check/call through to showdown
    gs_test.take_action(0, PlayerAction.CALL, 2)  # BB
    gs_test.take_action(1, PlayerAction.CHECK)    # SB
    # Flop
    gs_test.take_action(0, PlayerAction.CHECK)
    gs_test.take_action(1, PlayerAction.CHECK)
    # Turn
    gs_test.take_action(0, PlayerAction.CHECK)
    gs_test.take_action(1, PlayerAction.CHECK)
    # River
    gs_test.take_action(0, PlayerAction.CHECK)
    gs_test.take_action(1, PlayerAction.CHECK)

    # Now we should be at showdown
    assert gs_test.phase == GamePhase.SHOWDOWN

    # Both players should have valid hands
    winners = gs_test.get_winners()
    assert len(winners) > 0  # Should have at least one winner


def test_get_player_state():
    """Test getting a player's state snapshot."""
    gs = GameState(num_players=2)

    # Get player 0 state
    p0_state = gs.get_player_state(0)
    assert isinstance(p0_state, PlayerState)
    assert p0_state.player_id == 0
    assert p0_state.stack == 99  # SB posted 1
    assert p0_state.bet_this_round == 1
    assert p0_state.total_bet == 1
    assert len(p0_state.hole_cards) == 2
    assert p0_state.is_active == True
    assert p0_state.is_all_in == False

    # Test invalid player ID
    assert gs.get_player_state(-1) is None
    assert gs.get_player_state(2) is None  # Out of range for 2 players


def test_get_game_state_snapshot():
    """Test getting the full game state snapshot."""
    gs = GameState(num_players=2)

    snapshot = gs.get_game_state_snapshot()

    assert isinstance(snapshot, dict)
    assert 'phase' in snapshot
    assert 'pot' in snapshot
    assert 'current_bet' in snapshot
    assert 'dealer_position' in snapshot
    assert 'board_cards' in snapshot
    assert 'players' in snapshot
    assert 'action_history' in snapshot
    assert 'current_player' in snapshot

    assert snapshot['phase'] == GamePhase.PREFLOP.name
    assert snapshot['pot'] == 3
    assert snapshot['current_bet'] == 2
    assert len(snapshot['board_cards']) == 0
    assert len(snapshot['players']) == 2
    assert isinstance(snapshot['players'][0], PlayerState)
    assert isinstance(snapshot['players'][1], PlayerState)
    assert snapshot['current_player'] == 2 % 2  # Should be 0 (first to act after BB)


def test_is_hand_complete():
    """Test checking if the hand is complete."""
    gs = GameState(num_players=2)

    # Initially should not be complete
    assert gs.is_hand_complete() == False

    # If one player folds, should be complete
    gs.take_action(0, PlayerAction.FOLD)
    assert gs.is_hand_complete() == True

    # Test that a hand with one player left is complete
    gs3 = GameState(num_players=2)
    gs3.take_action(0, PlayerAction.FOLD)  # Player 0 (first to act) folds
    assert gs3.is_hand_complete() == True


if __name__ == "__main__":
    pytest.main([__file__])