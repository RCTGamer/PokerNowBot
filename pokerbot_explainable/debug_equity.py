from pokerbot_explainable.core.hand_evaluator import HandEvaluator
from pokerbot_explainable.core.card_utils import Card, Suit, Rank

# Test the specific case
eval = HandEvaluator(mcmc_samples=2000)  # Increase sample size for better accuracy
hand = [
    Card(Rank.ACE, Suit.SPADES),
    Card(Rank.KING, Suit.DIAMONDS),
]
board = [
    Card(Rank.ACE, Suit.HEARTS),
    Card(Rank.JACK, Suit.HEARTS),
    Card(Rank.TWO, Suit.CLUBS),
]

print("Testing As Kd on Ah Jh 2c board:")
print("Hand: Pair of Aces with King kicker")

# Run multiple times to see variance
results = []
for i in range(5):
    equity = eval.equity_vs_random(board, hand, num_opponents=1)
    results.append(equity)
    print(f"  Run {i+1}: {equity:.4f}")

print(f"  Average: {sum(results)/len(results):.4f}")
print(f"  Range: {min(results):.4f} - {max(results):.4f}")