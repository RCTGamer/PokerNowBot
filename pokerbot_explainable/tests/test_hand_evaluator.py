"""Unit tests for hand_evaluator module."""
import pytest

from pokerbot_explainable.core.hand_evaluator import HandEvaluator
from pokerbot_explainable.core.card_utils import Card, Suit, Rank


def test_hand_evaluator_creation():
    eval = HandEvaluator()
    assert eval._use_treys is True
    assert eval._mcmc_samples == 1000


def test_royal_flush():
    eval = HandEvaluator(mcmc_samples=100)  # small for speed
    # Royals: Ah Kh Qh Jh Th
    hand = [
        Card(Rank.ACE, Suit.HEARTS),
        Card(Rank.KING, Suit.HEARTS),
    ]
    board = [
        Card(Rank.QUEEN, Suit.HEARTS),
        Card(Rank.JACK, Suit.HEARTS),
        Card(Rank.TEN, Suit.HEARTS),
    ]
    rank, hand_class = eval.evaluate_hand(board, hand)
    # Treys treats royal flush as straight flush
    assert hand_class == "straight flush"


def test_pair():
    eval = HandEvaluator(mcmc_samples=100)
    hand = [
        Card(Rank.ACE, Suit.CLUBS),
        Card(Rank.ACE, Suit.DIAMONDS),
    ]
    board = [
        Card(Rank.KING, Suit.SPADES),
        Card(Rank.SEVEN, Suit.HEARTS),
        Card(Rank.TWO, Suit.DIAMONDS),
    ]
    rank, hand_class = eval.evaluate_hand(board, hand)
    assert hand_class == "pair"


def test_equity_vs_random():
    eval = HandEvaluator(mcmc_samples=200)  # low for speed
    # Pair of aces preflop should have ~85% equity vs one random hand
    hand = [
        Card(Rank.ACE, Suit.CLUBS),
        Card(Rank.ACE, Suit.HEARTS),
    ]
    board = []  # preflop
    equity = eval.equity_vs_random(board, hand, num_opponents=1)
    # Expect around 0.85; allow tolerance due to MC
    assert 0.78 <= equity <= 0.88


def test_equity_with_board():
    eval = HandEvaluator(mcmc_samples=200)
    # Top pair on flop: As Kd on Ah Jh 2c
    hand = [
        Card(Rank.ACE, Suit.SPADES),
        Card(Rank.KING, Suit.DIAMONDS),
    ]
    board = [
        Card(Rank.ACE, Suit.HEARTS),
        Card(Rank.JACK, Suit.HEARTS),
        Card(Rank.TWO, Suit.CLUBS),
    ]
    equity = eval.equity_vs_random(board, hand, num_opponents=1)
    # Top pair good kicker vs random ~0.80?
    assert 0.75 <= equity <= 0.85