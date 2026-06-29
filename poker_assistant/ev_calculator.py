"""
Expected Value (EV) calculation module.
Provides Monte Carlo simulation for estimating EV of actions given opponent range.
"""

import random
from typing import List, Tuple, Dict, Any, Optional

try:
    from deuces import Card, Evaluator
    DEUCES_AVAILABLE = True
except ImportError:
    DEUCES_AVAILABLE = False
    # warning will be printed in EVCalculator.__init__

# Helper to convert string card to deuces Card
def _to_deuces(card_str: str):
    if not DEUCES_AVAILABLE:
        return None
    rank_map = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
    suit_map = {'s':0,'h':1,'d':2,'c':3}
    return Card.new(rank_map[card_str[0]] + suit_map[card_str[1]])

class EVCalculator:
    def __init__(self, opponent_model, num_simulations: int = 2000):
        """
        :param opponent_model: Object providing get_range() returning list of (combo, prob)
        :param num_simulations: Number of Monte Carlo rollouts per action
        """
        self.opponent = opponent_model
        self.num_sims = num_simulations
        if DEUCES_AVAILABLE:
            self.evaluator = Evaluator()
        # Precompute full deck
        self.ranks = '23456789TJQKA'
        self.suits = 'shdc'
        self.full_deck = [r+s for r in self.ranks for s in self.suits]
        self._hand_strength_cache = {}  # optional cache

    def _remove_known(self, hole: List[str], board: List[str]) -> List[str]:
        used = set(hole + board)
        return [c for c in self.full_deck if c not in used]

    def _hand_showdown_value(self, our_hole: List[str], opp_hole: List[str],
                            board: List[str]) -> float:
        """
        Returns 1 if we win, 0 if we lose, 0.5 for tie.
        Uses deuces if available, else fallback heuristic.
        """
        if DEUCES_AVAILABLE and len(board) >= 3:
            try:
                our_cards = [_to_deuces(c) for c in our_hole]
                opp_cards = [_to_deuces(c) for c in opp_hole]
                board_cards = [_to_deuces(c) for c in board]
                our_score = self.evaluator.evaluate(board_cards, our_cards)
                opp_score = self.evaluator.evaluate(board_cards, opp_cards)
                if our_score < opp_score:
                    return 1.0
                elif our_score > opp_score:
                    return 0.0
                else:
                    return 0.5
            except Exception:
                pass  # fallback
        # Fallback: compare hand strength heuristic
        our_str = self._hand_strength_heuristic(our_hole, board)
        opp_str = self._hand_strength_heuristic(opp_hole, board)
        if our_str > opp_str + 0.05:
            return 1.0
        elif our_str < opp_str - 0.05:
            return 0.0
        else:
            return 0.5

    def _hand_strength_heuristic(self, hole: List[str], board: List[str]) -> float:
        """
        Very simple heuristic: probability of being best given random opponent hand.
        Not accurate; placeholder.
        """
        # Use preflop strength for simplicity; could be improved.
        return self._preflop_strength(tuple(sorted(hole)))

    def _preflop_strength(self, combo: tuple) -> float:
        """
        Preflop hand strength (0-1) based on equity vs random hand.
        Approximate using known tables; we'll use a simple formula.
        """
        # Use known approximations: Pair AA=0.85, KK=0.82, etc.
        # For simplicity, use rank and suitedness.
        if not DEUCES_AVAILABLE:
            # Use same heuristic as opponent model
            return self.opponent._combo_strength(combo) if hasattr(self.opponent, '_combo_strength') else 0.5
        # Use actual equity via enumeration vs random (could be heavy)
        # We'll approximate with a known mapping: we can compute using-deuces vs one random hand many times.
        # For speed, we return placeholder.
        return 0.5

    def _sample_action_likelihood(self, action: str, our_hole: List[str],
                                 board: List[str], pot: float,
                                 bet_to_call: float, raise_size: float) -> float:
        """
        Placeholder: probability opponent takes given action given our action.
        Not used directly; we instead simulate opponent's hand and then decide their reaction
        based on hand strength.
        """
        return 0.5

    def simulate_action(self, our_hole: List[str], board: List[str],
                       pot: float, bet_to_call: float,
                       action: str, bet_size: float = 0.0,
                       opponent_stack: float = None,
                       our_stack: float = None) -> float:
        """
        Monte Carlo estimate of EV for taking `action`.
        Returns EV in same units as pot (e.g., chips).
        Simple model: after our action, we assume showdown (no further betting)
        except we model opponent folding to a bet/raise with some probability.
        """
        if action == 'fold':
            return 0.0  # lose no additional chips (sunk cost already in pot)

        range_dist = self.opponent.get_range()  # list of ((c1,c2), prob)
        if not range_dist:
            # fallback uniform
            range_dist = [((r1+s1, r2+s2), 1.0/len(self.full_dack)) for i, (r1,s1) in enumerate(...) ]  # skip
            # For simplicity, we'll just use a few hands
            range_dist = [(('As','Kh'),0.3), (('Kd','Kc'),0.3), (('7c','5c'),0.4)]

        total_ev = 0.0
        for _ in range(self.num_sims):
            # Sample opponent hole from distribution
            combos, probs = zip(*range_dist)
            idx = random.choices(range(len(combos)), weights=probs)[0]
            opp_hole = list(combos[idx])
            # Determine remaining board cards
            needed = 5 - len(board)
            if needed > 0:
                deck_avail = self._remove_known(our_hole + opp_hole, board)
                runout = random.sample(deck_avail, needed)
                full_board = board + runout
            else:
                full_board = board

            # Determine opponent reaction to our bet/raise (if any)
            # Simple model: opponent folds with probability decreasing with hand strength
            opp_strength = self._hand_strength_heuristic(opp_hole, full_board)
            # probability they continue (call/raise) increases with strength
            p_continue = 0.1 + 0.8 * opp_strength  # range [0.1,0.9]
            if action in ('bet', 'raise') and bet_size > 0:
                # They may fold
                if random.random() > p_continue:  # they fold
                    # We win the pot (they don't call our bet)
                    payoff = pot  # we win what's already in pot
                    total_ev += payoff
                    continue  # go to next simulation
                # else they call (or raise) -> showdown
            # If we called or they called, go to showdown
            result = self._hand_showdown_value(our_hole, opp_hole, full_board)
            if action == 'call':
                # We call bet_to_call, then showdown
                if result == 1.0:
                    payoff = pot + bet_to_call  # we win pot + opponent's call
                elif result == 0.5:
                    payoff = bet_to_call  # split pot, we get our call back
                else:
                    payoff = -bet_to_call  # lose our call
                total_ev += payoff
            elif action in ('bet', 'raise'):
                # We bet/bet_size (in addition to any call amount?)
                # Assume bet_size is the size of our bet/raise
                # If we already called bet_to_call to stay in, then total we put in pot = bet_to_call + bet_size
                # For simplicity, treat bet_size as total additional chips we put in pot this street
                # We'll treat bet_to_call as 0 for bet/raise actions (i.e., we are the bettor)
                total_commitment = bet_to_call + bet_size
                if result == 1.0:
                    payoff = pot + bet_to_call + bet_size  # we win pot + their call + our bet
                elif result == 0.5:
                    payoff = bet_to_call + bet_size  # split
                else:
                    payoff = -(bet_to_call + bet_size)
                total_ev += payoff
            else:
                # default as call
                if result == 1.0:
                    payoff = pot + bet_to_call
                elif result == 0.5:
                    payoff = bet_to_call
                else:
                    payoff = -bet_to_call
                total_ev += payoff

        return total_ev / self.num_sims

    def compute_action_evs(self, our_hole: List[str], board: List[str],
                          pot: float, bet_to_call: float,
                          raise_sizes: List[float] = None) -> Dict[str, float]:
        """
        Compute EV for a set of actions: fold, call, raise(s).
        Returns dict mapping action label to EV.
        """
        if raise_sizes is None:
            # default: pot-sized raise
            raise_sizes = [pot * 0.5, pot * 1.0, pot * 2.0]
        evs = {
            'fold': self.simulate_action(our_hole, board, pot, bet_to_call, 'fold', 0.0),
            'call': self.simulate_action(our_hole, board, pot, bet_to_call, 'call', 0.0),
        }
        for rs in raise_sizes:
            label = f'raise_{int(rs)}' if rs.is_integer() else f'raise_{rs:.2f}'
            evs[label] = self.simulate_action(our_hole, board, pot, bet_to_call, 'raise', rs)
        return evs

# Example usage and simple test
if __name__ == "__main__":
    # Mock opponent model
    class MockOpponentModel:
        def get_range(self):
            # Return a few hands with equal weight
            return [('As','Kh'), ('Qd','Qh'), ('7c','5c')]
        def _combo_strength(self, combo):
            # dummy
            return 0.5
    opp = MockOpponentModel()
    calc = EVCalculator(opp, num_simulations=500)
    our_hand = ['As', 'Ad']
    board = ['Ah', 'Kd', '9c']
    pot = 6.0
    bet_to_call = 2.0  # opponent bet 2 into pot of 6
    evs = calc.compute_action_evs(our_hand, board, pot, bet_to_call, [2.0, 4.0])
    print("EV per action:")
    for act, ev in evs.items():
        print(f"  {act}: {ev:.3f}")
    best = max(evs, key=evs.get)
    print(f"Best action: {best} ({evs[best]:.3f})")