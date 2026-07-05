"""Card representation and deck utilities."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
import random


class Suit(Enum):
    CLUBS = "c"
    DIAMONDS = "d"
    HEARTS = "h"
    SPADES = "s"


class Rank(Enum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        rank_map = {
            14: "A",
            13: "K",
            12: "Q",
            11: "J",
            10: "T",
        }
        rank_str = rank_map.get(self.rank.value, str(self.rank.value))
        return f"{rank_str}{self.suit.value}"

    @classmethod
    def from_str(cls, s: str) -> "Card":
        """Parse a card string like 'Ah' or 'Ts'."""
        if len(s) != 2:
            raise ValueError(f"Invalid card string: {s}")
        rank_char, suit_char = s[0], s[1]
        rank_map = {
            "A": Rank.ACE,
            "K": Rank.KING,
            "Q": Rank.QUEEN,
            "J": Rank.JACK,
            "T": Rank.TEN,
            "9": Rank.NINE,
            "8": Rank.EIGHT,
            "7": Rank.SEVEN,
            "6": Rank.SIX,
            "5": Rank.FIVE,
            "4": Rank.FOUR,
            "3": Rank.THREE,
            "2": Rank.TWO,
        }
        suit_map = {
            "c": Suit.CLUBS,
            "d": Suit.DIAMONDS,
            "h": Suit.HEARTS,
            "s": Suit.SPADES,
        }
        try:
            rank = rank_map[rank_char.upper()]
        except KeyError:
            raise ValueError(f"Invalid rank character: {rank_char}")
        try:
            suit = suit_map[suit_char]
        except KeyError:
            raise ValueError(f"Invalid suit character: {suit_char}")
        return cls(rank, suit)


class Deck:
    """Standard 52-card deck."""

    def __init__(self) -> None:
        self.cards: List[Card] = [
            Card(rank, suit)
            for suit in Suit
            for rank in Rank
        ]
        self._index = 0

    def shuffle(self) -> None:
        random.shuffle(self.cards)
        self._index = 0

    def deal(self) -> Card:
        if self._index >= len(self.cards):
            raise ValueError("Deck is empty")
        card = self.cards[self._index]
        self._index += 1
        return card

    def deal_hand(self, n: int = 2) -> List[Card]:
        return [self.deal() for _ in range(n)]

    def remaining(self) -> int:
        return len(self.cards) - self._index

    def __len__(self) -> int:
        return len(self.cards) - self._index

    def __str__(self) -> str:
        return f"Deck({len(self)} cards remaining)"
