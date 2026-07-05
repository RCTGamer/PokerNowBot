import sys
sys.path.insert(0, 'C:\\Users\\RCT\\Desktop\\PokerNowBot\\pokerbot_explainable')

from treys import Card as TreysCard, Deck as TreysDeck, Evaluator
from pokerbot_explainable.core.card_utils import Card, Suit, Rank

# Test our conversion
hand = [
    Card(Rank.ACE, Suit.HEARTS),
    Card(Rank.KING, Suit.HEARTS),
]
board = [
    Card(Rank.QUEEN, Suit.HEARTS),
    Card(Rank.JACK, Suit.HEARTS),
    Card(Rank.TEN, Suit.HEARTS),
]

print("Our cards:")
for c in hand + board:
    print(f"  {c.rank.name} of {c.suit.name}")

# Convert to treys
treys_hand = [TreysCard.new(str(c)) for c in hand]
treys_board = [TreysCard.new(str(c)) for c in board]

print("\nTrey's cards:")
print(f"  Hand: {[str(c) for c in treys_hand]}")
print(f"  Board: {[str(c) for c in treys_board]}")

# Evaluate
evaluator = Evaluator()
rank = evaluator.evaluate(treys_board, treys_hand)
print(f"\nRank: {rank}")
class_id = evaluator.get_rank_class(rank)
print(f"Class ID: {class_id}")
class_string = evaluator.class_to_string(class_id)
print(f"Class string: {class_string}")

# Check our mapping
from pokerbot_explainable.core.hand_evaluator import HandEvaluator
he = HandEvaluator()
print(f"\nOur mapping for class {class_id}: {he.RANK_CLASS_TO_STRING.get(class_id, 'NOT FOUND')}")
print(f"Full mapping: {he.RANK_CLASS_TO_STRING}")