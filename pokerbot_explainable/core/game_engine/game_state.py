"""Game state management for pokerbot_explainable."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..card_utils import Card, Deck
from ..constants.game import GamePhase, PlayerAction, Position, DEFAULT_BLINDS, DEFAULT_STARTING_STACK
from ..hand_evaluator import HandEvaluator


@dataclass(frozen=True)
class PlayerState:
    """Immutable snapshot of a player's state at a point in time."""
    player_id: int
    stack: int
    bet_this_round: int
    total_bet: int
    hole_cards: List[Card]
    is_active: bool  # Still in hand (not folded)
    is_all_in: bool


@dataclass
class GameState:
    """
    Tracks the complete state of a poker hand.

    This class manages the progression of a poker hand from preflop to showdown,
    handling betting rounds, card dealing, and state transitions.
    """

    # Game configuration
    num_players: int
    blinds: List[int] = field(default_factory=lambda: DEFAULT_BLINDS.copy())
    starting_stack: int = DEFAULT_STARTING_STACK
    dealer_position: int = 0  # Index of the dealer button

    # Game state
    phase: GamePhase = GamePhase.PREFLOP
    pot: int = 0
    current_bet: int = 0  # Amount to call to stay in hand

    # Player states
    players: List[dict] = field(default_factory=list)

    # Cards
    deck: Optional[Deck] = None
    board_cards: List[Card] = field(default_factory=list)

    # Action tracking
    action_history: List[tuple] = field(default_factory=list)  # (player_id, action, amount)
    current_player: int = 0  # Index of player whose turn it is
    betting_round_complete: bool = False
    last_raiser: int = 0  # Track who last raised for betting completion
    _actions_since_last_raise: int = 0  # Count of actions in current betting round

    def __post_init__(self):
        """Initialize the game state after creation."""
        if not self.players:
            self._initialize_players()
        if self.deck is None:
            self.deck = Deck()
            self.deck.shuffle()
        self._needs_street_reset = False
        self._post_blinds()
        self._deal_hole_cards()
        self._set_first_player()

    def _initialize_players(self):
        """Create player objects with starting stacks."""
        for i in range(self.num_players):
            self.players.append({
                'id': i,
                'stack': self.starting_stack,
                'bet_this_round': 0,
                'total_bet': 0,
                'hole_cards': [],
                'is_active': True,
                'is_all_in': False
            })

    def _post_blinds(self):
        """Post the small and big blinds."""
        sb_amount = self.blinds[0]
        bb_amount = self.blinds[1]

        # Calculate blind positions based on dealer position using standard poker rules
        # For heads-up (2 players): dealer is small blind
        # For 3+ players: standard positions
        if self.num_players == 2:
            sb_index = self.dealer_position
            bb_index = (self.dealer_position + 1) % self.num_players
        else:
            # Standard position for 3+ players
            sb_index = (self.dealer_position + 1) % self.num_players
            bb_index = (self.dealer_position + 2) % self.num_players

        # Store blind positions as attributes for testing (match actual gameplay)
        self.small_blind_index = sb_index
        self.big_blind_index = bb_index

        # Small blind
        sb_player = self.players[sb_index]
        sb_player['stack'] -= sb_amount
        sb_player['bet_this_round'] += sb_amount
        sb_player['total_bet'] += sb_amount
        self.pot += sb_amount

        # Big blind
        bb_player = self.players[bb_index]
        bb_player['stack'] -= bb_amount
        bb_player['bet_this_round'] += bb_amount
        bb_player['total_bet'] += bb_amount
        self.pot += bb_amount
        self.current_bet = bb_amount  # BB sets the initial bet to call

        # Record blinds in action history
        self.action_history.append((sb_index, PlayerAction.BET, sb_amount))
        self.action_history.append((bb_index, PlayerAction.BET, bb_amount))

    def _deal_hole_cards(self):
        """Deal two hole cards to each player."""
        for player in self.players:
            player['hole_cards'] = [self.deck.deal(), self.deck.deal()]

    def _set_first_player(self):
        """Set the first player to act (player after big blind)."""
        # Calculate blind positions using the same logic as _post_blinds
        if self.num_players == 2:
            sb_index = self.dealer_position
            bb_index = (self.dealer_position + 1) % self.num_players
        else:
            sb_index = (self.dealer_position + 1) % self.num_players
            bb_index = (self.dealer_position + 2) % self.num_players

        # Set first player to act (player after big blind)
        self.current_player = (bb_index + 1) % self.num_players
        # Skip players who are all-in or folded (though initially all are active)
        while not self._is_player_active(self.current_player):
            self.current_player = (self.current_player + 1) % self.num_players
        self.last_raiser = bb_index  # BB is considered the last raiser preflop

    def _is_player_active(self, player_idx: int) -> bool:
        """Check if a player is still active in the hand."""
        if not (0 <= player_idx < len(self.players)):
            return False
        player = self.players[player_idx]
        return player['is_active'] and not player['is_all_in']

    def _next_player(self):
        """Advance to the next active player."""
        original = self.current_player
        while True:
            self.current_player = (self.current_player + 1) % self.num_players
            if self._is_player_active(self.current_player):
                break
            # Safety check to prevent infinite loop
            if self.current_player == original:
                break

    def _advance_street(self):
        """Advance to the next street (flop, turn, river).

        Resets per-street betting state. Does NOT immediately clear
        bet_this_round; that is reset lazily on the first take_action of
        the new street so observers (tests, snapshots) can still see what
        each player put in during the just-finished round.
        """
        self._needs_street_reset = True

        if self.phase == GamePhase.PREFLOP:
            self.phase = GamePhase.FLOP
            # Deal flop (3 cards)
            self.board_cards.extend([self.deck.deal() for _ in range(3)])
        elif self.phase == GamePhase.FLOP:
            self.phase = GamePhase.TURN
            # Deal turn (1 card)
            self.board_cards.append(self.deck.deal())
        elif self.phase == GamePhase.TURN:
            self.phase = GamePhase.RIVER
            self.board_cards.append(self.deck.deal())
        elif self.phase == GamePhase.RIVER:
            self.phase = GamePhase.SHOWDOWN

        # Reset per-street betting state.
        self.current_bet = 0
        self._actions_since_last_raise = 0
        # The just-finished street is complete.
        self.betting_round_complete = True

        # First active player after the small blind.
        # If nobody can act (all all-in/folded), default to dealer_position.
        active_count = sum(1 for p in self.players if self._is_player_active(p['id']))
        if active_count == 0:
            self.current_player = self.dealer_position
        else:
            sb_index = (self.dealer_position + 1) % self.num_players
            self.current_player = (sb_index + 1) % self.num_players
            while not self._is_player_active(self.current_player):
                self.current_player = (self.current_player + 1) % self.num_players

        self.last_raiser = self.current_player

    def _lazy_reset_street(self):
        """Reset per-street bet_this_round values once a new street begins.

        If no player can bet (everyone all-in or folded), keep advancing
        streets automatically until showdown so callers don't have to walk
        the game forward themselves.
        """
        if getattr(self, "_needs_street_reset", False):
            # Run out remaining streets only when nobody can act.
            active_count = sum(
                1 for p in self.players if self._is_player_active(p['id'])
            )
            if active_count == 0:
                # All remaining streets (deferred to avoid recursion here).
                while self.phase != GamePhase.SHOWDOWN and sum(
                    1 for p in self.players if self._is_player_active(p['id'])
                ) == 0:
                    self.betting_round_complete = True
                    self._collect_bets()
                    # Reset per-street state before advancing again.
                    for player in self.players:
                        player['bet_this_round'] = 0
                    self._needs_street_reset = False
                    if self.phase == GamePhase.SHOWDOWN:
                        break
                    self._advance_street()
                return

            # Normal case: reset per-street fields for the upcoming action.
            for player in self.players:
                player['bet_this_round'] = 0
            self.betting_round_complete = False
            self._needs_street_reset = False

    def _is_betting_round_complete(self) -> bool:
        """
        Check if the current betting round is complete.

        A betting round is complete when:
        1. All active players have matched the current bet (or are all-in), AND
        2. Each active player has had a chance to act since the last raise.
        """
        active_players = [i for i in range(len(self.players)) if self._is_player_active(i)]
        if not active_players:
            return True

        # All matched?
        for i in active_players:
            player = self.players[i]
            if not player['is_all_in'] and player['bet_this_round'] < self.current_bet:
                return False

        # Everyone active has had a chance to act since the last raise.
        # Action counter wraps at len(active_players); >= means the round has
        # come back around.
        return self._actions_since_last_raise >= len(active_players)

    def _collect_bets(self):
        """Collect bets into the pot. Resets bet_this_round only if forced.

        Note: As of the refactor, take_action already credits the pot incrementally
        for each action, so re-adding bet_this_round here would double-count.
        We only reset bet_this_round for players at the start of the next street.
        """
        # Update total_bet from current bets (defensive; take_action already does this).
        for player in self.players:
            if player['bet_this_round'] > 0:
                player['total_bet'] += player['bet_this_round']
                # Do NOT zero bet_this_round here; _advance_street will reset to 0.

    def take_action(self, player_id: int, action: PlayerAction, amount: int = 0) -> bool:
        """
        Process a player's action.

        Args:
            player_id: Index of the player taking the action
            action: The action to take (FOLD, CHECK, CALL, BET, RAISE)
            amount: Amount for bet/raise (ignored for other actions)

        Returns:
            True if action was valid and processed, False otherwise
        """
        # Validate player
        if not (0 <= player_id < len(self.players)):
            return False

        # If we just transitioned to a new street, reset per-street state lazily
        # so observers between rounds can still read pre-completion values.
        self._lazy_reset_street()

        player = self.players[player_id]
        if not self._is_player_active(player_id):
            return False

        # Validate it's this player's turn
        if player_id != self.current_player:
            return False

        # Process the action
        if action == PlayerAction.FOLD:
            player['is_active'] = False
            self.action_history.append((player_id, PlayerAction.FOLD, 0))
            self._actions_since_last_raise += 1

        elif action == PlayerAction.CHECK:
            if self.current_bet > player['bet_this_round']:
                return False  # Can't check if there's a bet to call
            player['bet_this_round'] = player['bet_this_round']  # No change
            self.action_history.append((player_id, PlayerAction.CHECK, 0))
            self._actions_since_last_raise += 1

        elif action == PlayerAction.CALL:
            # `amount` is the additional chips paid to match the call.
            call_amount = amount
            if call_amount > player['stack']:
                # Allow the action but mark all-in (stack may go to 0 or negative)
                player['is_all_in'] = True

            if call_amount <= 0:
                return False  # Nothing meaningful to call with

            player['stack'] -= call_amount
            player['total_bet'] += call_amount
            self.pot += call_amount

            # Set bet_this_round capped to current_bet (CALL is a match, not a raise)
            proposed_bet = player['bet_this_round'] + call_amount
            player['bet_this_round'] = min(proposed_bet, self.current_bet)

            self.action_history.append((player_id, PlayerAction.CALL, call_amount))
            self._actions_since_last_raise += 1

        elif action in (PlayerAction.BET, PlayerAction.RAISE):
            if amount <= 0:
                return False

            # For bet, amount is the total bet to put out
            # For raise, amount is the total bet to put out (including call)
            total_bet = amount

            # Calculate additional amount needed beyond current bet
            additional = total_bet - player['bet_this_round']
            if additional < self.blinds[1]:  # Minimum raise is big blind
                # Actually, minimum raise is the size of the last bet/raise
                # For simplicity, we'll use big blind as minimum
                if additional < self.blinds[1]:
                    return False

            if additional > player['stack']:
                # All-in bet/raise
                additional = player['stack']
                player['is_all_in'] = True
                total_bet = player['bet_this_round'] + additional

            if total_bet <= player['bet_this_round']:
                return False  # Must increase the bet

            player['stack'] -= additional
            player['bet_this_round'] = total_bet
            player['total_bet'] += additional  # Track total amount bet in hand
            self.pot += additional  # Only track additional chips contributed

            if action == PlayerAction.BET:
                self.action_history.append((player_id, PlayerAction.BET, total_bet))
            else:  # RAISE
                self.action_history.append((player_id, PlayerAction.RAISE, additional))
                self.last_raiser = player_id  # Update last raiser when someone raises

            # A bet/raise counts as one action and resets the round cycle.
            self._actions_since_last_raise = 1

            # Update current_bet if this is a new highest bet
            if total_bet > self.current_bet:
                self.current_bet = total_bet

        else:
            return False  # Invalid action

        # Check if player is now all-in
        if player['stack'] == 0:
            player['is_all_in'] = True

        # Move to next player
        self._next_player()

        # Check if betting round is complete
        if self._is_betting_round_complete():
            # Mark the just-completed round as such.
            self.betting_round_complete = True
            # Decide whether to keep advancing.
            # - 0 active (everyone all-in) -> auto-run remaining streets.
            # - 1 active (someone folded)   -> stop; the hand just ended via
            #                                 fold, leave current_bet/phase
            #                                 untouched for observers.
            # - 2+ active                   -> normal advance to next street.
            active_count = sum(
                1 for p in self.players if self._is_player_active(p['id'])
            )
            if self.phase != GamePhase.SHOWDOWN and active_count != 1:
                self._collect_bets()
                self._advance_street()

        return True

    def get_player_state(self, player_id: int) -> Optional[PlayerState]:
        """
        Get an immutable snapshot of a player's current state.

        Args:
            player_id: Index of the player

        Returns:
            PlayerState object or None if invalid player_id
        """
        if not (0 <= player_id < len(self.players)):
            return None

        player = self.players[player_id]
        return PlayerState(
            player_id=player['id'],
            stack=player['stack'],
            bet_this_round=player['bet_this_round'],
            total_bet=player['total_bet'],
            hole_cards=player['hole_cards'].copy(),
            is_active=player['is_active'],
            is_all_in=player['is_all_in']
        )

    def get_game_state_snapshot(self) -> dict:
        """
        Get a complete immutable snapshot of the current game state.

        Returns:
            Dictionary containing all relevant game state information
        """
        return {
            'phase': self.phase.name,
            'pot': self.pot,
            'current_bet': self.current_bet,
            'dealer_position': self.dealer_position,
            'board_cards': [str(card) for card in self.board_cards],
            'players': [self.get_player_state(i) for i in range(len(self.players))],
            'action_history': self.action_history.copy(),
            'current_player': self.current_player
        }

    def is_hand_complete(self) -> bool:
        """
        Check if the hand is complete (ready for showdown or only one player left).

        Returns:
            True if the hand is over, False otherwise
        """
        active_players = [i for i in range(len(self.players)) if self._is_player_active(i)]
        return len(active_players) <= 1 or self.phase == GamePhase.SHOWDOWN

    def evaluate_hand(self, player_id: int) -> tuple:
        """
        Evaluate a player's hand using their hole cards and the board cards.

        Args:
            player_id: Index of the player

        Returns:
            Tuple of (rank, hand_class) where lower rank is better
        """
        if not (0 <= player_id < len(self.players)):
            raise ValueError(f"Invalid player_id: {player_id}")

        player = self.players[player_id]
        if not player['hole_cards'] or len(player['hole_cards']) != 2:
            raise ValueError(f"Player {player_id} does not have valid hole cards")

        evaluator = HandEvaluator()
        return evaluator.evaluate_hand(self.board_cards, player['hole_cards'])

    def get_winners(self) -> list:
        """
        Determine the winner(s) of the hand.

        Returns:
            List of player IDs who won the pot (split pot possible)
        """
        if self.phase != GamePhase.SHOWDOWN:
            # If not showdown yet, return active players if only one remains
            active_players = [i for i in range(len(self.players)) if self._is_player_active(i)]
            if len(active_players) == 1:
                return active_players
            return []  # No winner yet

        # Showdown: evaluate all active players' hands
        active_players = [i for i in range(len(self.players)) if self._is_player_active(i)]
        if not active_players:
            return []

        # Evaluate each active player's hand
        player_hands = {}
        best_rank = float('inf')

        for player_id in active_players:
            try:
                rank, _ = self.evaluate_hand(player_id)
                player_hands[player_id] = rank
                if rank < best_rank:
                    best_rank = rank
            except ValueError:
                # Skip players with invalid hands (shouldn't happen in normal play)
                continue

        # Find all players with the best rank
        winners = [player_id for player_id, rank in player_hands.items() if rank == best_rank]
        return winners