"""
Opponent modeling module.
Maintains a probability distribution over opponent hole card combinations (or buckets).
Updates based on observed actions using Bayesian updating.
"""

from typing import List, Tuple, Dict, Optional
from collections import defaultdict
import math
import itertools

# All possible hole card combinations (1326 combos)
RANKS = '23456789TJQKA'
SUITS = 'shdc'
ALL_CARDS = [r+s for r in RANKS for s in SUITS]

def all_combinations() -> List[tuple]:
    """Return list of all distinct hole card combinations (suitedness matters)."""
    combos = []
    for i in range(len(ALL_CARDS)):
        for j in range(i+1, len(ALL_CARDS)):
            c1, c2 = ALL_CARDS[i], ALL_CARDS[j]
            # Ensure consistent ordering for hashing
            combos.append(tuple(sorted((c1, c2))))
    return combos

ALL_COMBOS = all_combinations()  # length 1326

class OpponentModel:
    def __init__(self, name: str = "opponent"):
        self.name = name
        # Prior: uniform over all combos
        self.weights = {combo: 1.0 for combo in ALL_COMBOS}
        self.total_weight = float(len(ALL_COMBOS))
        # Seen actions history for debugging
        self.history = []
        # Simple opponent tendencies (will be updated)
        self.vpip = 0.0  # voluntary put money in pot
        self.pfr = 0.0   # preflop raise
        self.three_bet = 0.0
        self.fold_to_cbet = 0.0
        self.actions_seen = 0

    def _combo_strength(self, combo: tuple) -> float:
        """
        Heuristic hand strength (0-1) for a hole card combo.
        Based on rank and suitedness/connectivity.
        """
        c1, c2 = combo
        r1, s1 = c1[0], c1[1]
        r2, s2 = c2[0], c2[1]
        rank_values = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
        r1v = rank_values[r1]
        r2v = rank_values[r2]
        suited = (s1 == s2)
        gap = abs(r1v - r2v) - 1  # 0 for paired, -1 for connected? Actually pair gap negative
        # Pair bonus
        if r1v == r2v:
            base = 0.8 + (r1v - 2) * 0.02  # pairs from 0.8 (22) to 1.0 (AA)
        else:
            # High card strength
            high = max(r1v, r2v)
            low = min(r1v, r2v)
            base = 0.3 + (high - 2) * 0.04  # Ace-high ~0.3+12*0.04=0.78? Adjust
            # Suited bonus
            if suited:
                base += 0.05
            # Connectedness (small gap)
            if gap <= 1:
                base += 0.05
            # Penalize large gaps
            if gap >= 3:
                base -= 0.05
        # Clamp
        return max(0.0, min(1.0, base))

    def get_range(self) -> List[tuple]:
        """
        Return list of (combo, probability) normalized.
        """
        if self.total_weight == 0:
            # Reset to uniform
            self.__init__(self.name)
        probs = {combo: w/self.total_weight for combo, w in self.weights.items()}
        # Return as list sorted by probability descending for convenience
        sorted_items = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        return sorted_items

    def update_with_action(self, action: str, street: str, context: dict):
        """
        Update weights based on observed action.
        action: e.g., 'fold', 'call', 'bet', 'raise', 'check'
        street: 'preflop', 'flop', 'turn', 'river'
        context: may include 'position', 'bet_size', 'pot_before', etc.
        """
        self.actions_seen += 1
        # Update simple stats
        if street == 'preflop':
            if action in ['call', 'bet', 'raise']:
                self.vpip += 1
            if action in ['bet', 'raise']:
                self.pfr += 1
            if action == 'raise' and context.get('is_3bet', False):
                self.three_bet += 1
        elif street == 'flop' and action == 'fold' and context.get('facing_cbet', False):
            self.fold_to_cbet += 1

        # For each combo, compute likelihood of this action given the combo and context
        # Simplified likelihood model:
        # For each combo, compute hand strength (street-specific) and map to action probability.
        # We'll use a simple logistic function.
        for combo in self.weights:
            strength = self._combo_strength(combo)
            # Adjust street: post-flop strength could be updated with board, but we ignore for simplicity
            # Likelihood of action given strength
            likelihood = self._action_likelihood(action, strength, street, context)
            self.weights[combo] *= likelihood
        # Renormalize
        self.total_weight = sum(self.weights.values())
        # Optional: resample to avoid super small numbers (not implemented)

    def _action_likelihood(self, action: str, strength: float, street: str, context: dict) -> float:
        """
        Return P(action | strength, street, context).
        Simple heuristic model.
        """
        # Base rates: assume player is average
        # We'll adjust based on strength and street
        if street == 'preflop':
            # Probability of VPIP (call/bet/raise) increases with strength
            if action == 'fold':
                return 1.0 - 0.8 * strength  # stronger hands less likely to fold
            elif action == 'call':
                return 0.3 * strength  # medium strength hands call
            elif action in ['bet', 'raise']:
                return 0.5 * strength  # strong hands raise
            else:
                return 0.01
        else:  # postflop
            # Simplified: liklihood of bet/raise increases with strength, call medium, fold weak
            if action == 'fold':
                return 1.0 - 0.9 * strength
            elif action == 'call':
                return 0.4 * (1.0 - abs(strength - 0.5)) * 2  # peak around medium
            elif action in ['bet', 'raise']:
                return 0.8 * strength
            else:
                return 0.01

    def get_vpip(self) -> float:
        if self.actions_seen == 0:
            return 0.0
        return self.vpip / self.actions_seen

    def get_pfr(self) -> float:
        if self.actions_seen == 0:
            return 0.0
        return self.pfr / self.actions_seen

    def get_three_bet_freq(self) -> float:
        if self.actions_seen == 0:
            return 0.0
        return self.three_bet / self.actions_seen

    def get_fold_to_cbet(self) -> float:
        # only count flop opportunities where faced cbet
        # simplify: use actions_seen as denominator
        if self.actions_seen == 0:
            return 0.0
        return self.fold_to_cbet / self.actions_seen

    def debug_top_hands(self, n: int = 10) -> List[tuple]:
        """Return top N combos with probabilities."""
        dist = self.get_range()
        return dist[:n]

# Example usage
if __name__ == "__main__":
    opp = OpponentModel("Hero")
    # Simulate seeing opponent fold preflop
    opp.update_with_action('fold', 'preflop', {})
    print("VPIP:", opp.get_vpip())
    print("PFR:", opp.get_pfr())
    top = opp.debug_top_hands(5)
    print("Top 5 hands after opponent fold:")
    for combo, prob in top:
        print(f"  {combo}: {prob:.4f}")