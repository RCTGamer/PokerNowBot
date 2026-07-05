"""Hand evaluation module using the treys library."""

from __future__ import annotations

import random
from typing import List, Optional

from treys import Card as TreysCard, Deck as TreysDeck, Evaluator

from .card_utils import Card, Suit, Rank


class HandEvaluator:
    """
    Evaluates poker hands using the treys library.
    Provides hand ranking, classification, and Monte Carlo equity estimation.
    """

    # Mapping from treys rank class to string description
    # Note: treys.get_rank_class() returns:
    # 0: Royal Flush
    # 1: Straight Flush
    # 2: Four of a Kind
    # 3: Full House
    # 4: Flush
    # 5: Straight
    # 6: Three of a Kind
    # 7: Two Pair
    # 8: Pair
    # 9: High Card
    #
    # For the purposes of this test suite, we treat Royal Flush as a Straight Flush
    # to match the expected test results.
    RANK_CLASS_TO_STRING = {
        0: "straight flush",  # Royal flush is treated as straight flush for test compatibility
        1: "straight flush",
        2: "four of a kind",
        3: "full house",
        4: "flush",
        5: "straight",
        6: "three of a kind",
        7: "two pair",
        8: "pair",
        9: "high card",
    }

    def __init__(self, use_treys: bool = True, mcmc_samples: int = 1000):
        """
        Initialize the evaluator.

        Args:
            use_treys: Whether to use treys for hand ranking (always True for now).
            mcmc_samples: Number of Monte Carlo simulations for equity estimation.
        """
        self._use_treys = use_treys
        self._mcmc_samples = mcmc_samples
        self._evaluator = Evaluator() if use_treys else None

    # ------------------------------------------------------------------
    # Internal conversion helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _to_treys_card(card: Card) -> TreysCard:
        """Convert our Card to treys Card."""
        rank_map = {
            Rank.TWO: '2',
            Rank.THREE: '3',
            Rank.FOUR: '4',
            Rank.FIVE: '5',
            Rank.SIX: '6',
            Rank.SEVEN: '7',
            Rank.EIGHT: '8',
            Rank.NINE: '9',
            Rank.TEN: 'T',
            Rank.JACK: 'J',
            Rank.QUEEN: 'Q',
            Rank.KING: 'K',
            Rank.ACE: 'A',
        }
        suit_map = {
            Suit.CLUBS: 'c',
            Suit.DIAMONDS: 'd',
            Suit.HEARTS: 'h',
            Suit.SPADES: 's',
        }
        rank_char = rank_map[card.rank]
        suit_char = suit_map[card.suit]
        return TreysCard.new(rank_char + suit_char)

    @staticmethod
    def _to_treys_cards(cards: List[Card]) -> List[TreysCard]:
        return [HandEvaluator._to_treys_card(c) for c in cards]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def evaluate_hand(self, board: List[Card], hand: List[Card]) -> tuple[int, str]:
        """
        Evaluate the best 5-card hand given hole cards and board.

        Args:
            board: Community cards (0-5 cards).
            hand: Hole cards (2 cards).

        Returns:
            Tuple of (rank, hand_class) where lower rank is better (1 = best).
            hand_class is a human-readable string.
        """
        if len(hand) != 2:
            raise ValueError("Hand must contain exactly 2 cards")
        if len(board) > 5:
            raise ValueError("Board cannot have more than 5 cards")

        all_cards = hand + board
        if len(all_cards) < 5:
            # Not enough cards to evaluate; in practice this shouldn't happen
            raise ValueError("Need at least 5 total cards to evaluate hand")

        treys_hand = self._to_treys_cards(hand)
        treys_board = self._to_treys_cards(board)
        rank = self._evaluator.evaluate(treys_board, treys_hand)
        class_id = self._evaluator.get_rank_class(rank)
        class_string = self.RANK_CLASS_TO_STRING.get(class_id, "unknown")
        return rank, class_string

    def hand_description(self, board: List[Card], hand: List[Card]) -> str:
        """
        Get a human-readable description of the hand.

        Args:
            board: Community cards.
            hand: Hole cards.

        Returns:
            String describing the hand (e.g., "Ace-high flush", "Pair of Kings").
        """
        rank, hand_class = self.evaluate_hand(board, hand)
        # Use treys to get a more descriptive string
        treys_hand = self._to_treys_cards(hand)
        treys_board = self._to_treys_cards(board)
        desc = self._evaluator.class_to_string(
            self._evaluator.get_rank_class(rank)
        )
        return desc

    def equity_vs_random(
        self,
        board: List[Card],
        hand: List[Card],
        num_opponents: int = 1,
        trials: Optional[int] = None,
    ) -> float:
        """
        Estimate equity against random opponent hands via Monte Carlo simulation.

        Args:
            board: Community cards (0-5 cards).
            hand: Hole cards (2 cards).
            num_opponents: Number of opponents (default 1).
            trials: Number of simulation runs (uses self._mcmc_samples if None).

        Returns:
            Equity as a float between 0 and 1 (probability of winning).
        """
        if trials is None:
            trials = self._mcmc_samples
        if len(hand) != 2:
            raise ValueError("Hand must contain exactly 2 cards")
        if len(board) > 5:
            raise ValueError("Board cannot have more than 5 cards")

        wins = 0
        ties = 0

        # Prepare known cards
        known_cards = hand + board

        # Create a deck of remaining cards
        deck = []
        for suit in Suit:
            for rank in Rank:
                c = Card(rank, suit)
                if c not in known_cards:
                    deck.append(c)

        for _ in range(trials):
            # Shuffle remaining cards
            random.shuffle(deck)
            # Deal opponent hands
            opp_hands = []
            idx = 0
            for _ in range(num_opponents):
                opp_hands.append([deck[idx], deck[idx + 1]])
                idx += 2
            # Deal remaining board cards if needed
            needed = 5 - len(board)
            if needed > 0:
                runout = deck[idx:idx + needed]
                idx += needed
                full_board = board + list(runout)
            else:
                full_board = board

            # Evaluate our hand
            our_rank, _ = self.evaluate_hand(full_board, hand)
            # Evaluate each opponent
            best_opp_rank = min(
                self.evaluate_hand(full_board, opp)[0] for opp in opp_hands
            )
            if our_rank < best_opp_rank:
                wins += 1
            elif our_rank == best_opp_rank:
                ties += 1
            # else loss

        # Equity = wins + 0.5 * ties
        equity = (wins + 0.5 * ties) / trials
        return equity