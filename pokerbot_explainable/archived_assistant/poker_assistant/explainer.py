"""
Explanation module for poker AI.
Generates human-readable explanations for recommendations based on EV, equity,
opponent modeling, SPR, and other factors.
"""

from typing import List, Tuple, Dict, Any, Optional

def format_hand(combo) -> str:
    """Convert (c1, c2) to readable string."""
    return ''.join(combo)

def explain_distribution(model_dist: List[tuple], top_n: int = 5) -> str:
    """
    Explain opponent range distribution.
    model_dist: list of (combo, probability) sorted descending.
    """
    top = model_dist[:top_n]
    lines = ["Opponent range estimate (top {}):".format(top_n)]
    for combo, prob in top:
        lines.append(f"  {format_hand(combo):<4} {prob*100:5.1f}%")
    # Sum of top probabilities
    top_mass = sum(prob for _, prob in top)
    lines.append(f"  Top {top_n} combos represent {top_mass*100:.1f}% of weighted range.")
    return "\n".join(lines)

def explain_ev(action_evs: dict, best_action: str, best_ev: float,
               pot_size: float, our_stack: float) -> str:
    """
    Explain expected value comparison.
    """
    lines = [f"Expected Value (in pot units):"]
    for action, ev in sorted(action_evs.items(), key=lambda x: x[1], reverse=True):
        bb = ev * pot_size  # Assuming pot expressed in big blinds? We'll treat as bet units.
        line = f"  {action:>6}: {ev:+.3f} pot units ({bb:+.2f} bb)"
        if action == best_action:
            line += " <-- BEST"
        lines.append(line)
    lines.append(f"Best action: {best_action.upper()} with EV {best_ev:.3f} pot units.")
    return "\n".join(lines)

def explain_spr(spr: float, pot: float, effective_stack: float) -> str:
    """
    Explain SPR implications.
    """
    category = "low" if spr < 4 else ("medium" if spr <= 10 else "high")
    lines = [
        f"Stack-to-Pot Ratio (SPR): {spr:.2f}",
        f"  Effective stack: {effective_stack:.2f}  Pot: {pot:.2f}",
        f"  SPR category: {category}"
    ]
    if category == "low":
        lines.append("  Implication: Pot is large relative to stacks; play is commitment-oriented.")
        lines.append("  Focus on strong made hands; draws have less implied value.")
    elif category == "medium":
        lines.append("  Implication: Balance between immediate and future money.")
        lines.append("  Both value betting and bluffing are viable.")
    else:
        lines.append("  Implication: Deep stacks; implied odds and position matter.")
        lines.append("  Speculative hands gain value; more room for bluffing and floating.")
    return "\n".join(lines)

def explain_opponent_stats(model: object) -> str:
    """
    Explain opponent tendencies from model.
    Expect model to have methods get_vpip, get_pfr, get_three_bet_freq, get_fold_to_cbet.
    """
    lines = ["Opponent tendencies:"]
    try:
        vpip = model.get_vpip()
        pfr = model.get_pfr()
        three_bet = model.get_three_bet_freq()
        fold_cbet = model.get_fold_to_cbet()
        lines.append(f"  VPIP: {vpip*100:5.1f}%")
        lines.append(f"  PFR:  {pfr*100:5.1f}%")
        lines.append(f"  3bet: {three_bet*100:5.1f}%")
        lines.append(f"  Fold to cbet: {fold_cbet*100:5.1f}%")
    except AttributeError:
        lines.append("  (detailed stats not available)")
    return "\n".join(lines)

def explain_recommendation(action: str, ev: float,
                           equity_vs_range: float,
                           pot_odds: float,
                           spr: float,
                           notes: Optional[List[str]] = None) -> str:
    """
    Build a full explanation for a recommended action.
    """
    lines = [f"Recommended action: {action.upper()}"]
    lines.append(f"  Expected value: {ev:+.3f} pot units")
    lines.append(f"  Equity vs opponent range: {equity_vs_range*100:.1f}%")
    if pot_odds > 0:
        lines.append(f"  Pot odds required: {pot_odds*100:.1f}%")
        if equity_vs_range > pot_odds:
            lines.append(f"  Equity exceeds pot odds -> profitable call.")
        else:
            lines.append(f"  Equity below pot odds -> call is losing.")
    lines.append(f"  SPR: {spr:.2f}")
    if notes:
        lines.append("  Notes:")
        for n in notes:
            lines.append(f"    - {n}")
    return "\n".join(lines)

def generate_full_report(model, board: List[str], pot: float,
                         effective_stack: float, action_evs: dict,
                         best_action: str, our_hand: List[str]) -> str:
    """
    Create a comprehensive report.
    """
    # Compute SPR
    spr = effective_stack / pot if pot > 0 else float('inf')
    # Get opponent distribution
    dist = model.get_range()
    # Estimate equity vs range (placeholder)
    equity = 0.5  # In real system, compute via equity enumeration
    # Pot odds for calling (assuming call cost is current bet to call)
    call_cost = action_evs.get('call', 0.0)  # not correct; but we can pass separately
    # For simplicity assume call cost = 1 unit
    pot_odds = 1.0 / (pot + 1.0) if pot > 0 else 0

    sections = []
    sections.append("=== POKER ANALYSIS REPORT ===")
    sections.append(f"Hero hand: {' '.join(our_hand)}")
    sections.append(f"Board: {' '.join(board) if board else '(preflop)'}")
    sections.append("")
    sections.append(explain_spr(spr, pot, effective_stack))
    sections.append("")
    sections.append(explain_opponent_stats(model))
    sections.append("")
    sections.append(explain_distribution(dist, top_n=5))
    sections.append("")
    sections.append(explain_ev(action_evs, best_action,
                               max(action_evs.values()), pot, effective_stack))
    sections.append("")
    notes = []
    if equity > 0.5:
        notes.append("You have above-average equity vs opponent range.")
    else:
        notes.append("Your equity is below average; consider folding unless implied odds.")
    if spr < 4:
        notes.append("Low SPR reduces bluff effectiveness; prioritize value hands.")
    elif spr > 10:
        notes.append("High SPR increases implied odds; speculative hands gain value.")
    sections.append(explain_recommendation(best_action,
                                           max(action_evs.values()),
                                           equity,
                                           pot_odds,
                                           spr,
                                           notes))
    sections.append("================================")
    # Ensure ASCII output to avoid encoding issues on Windows
    result = "\n".join(sections)
    return result.encode("ascii", "ignore").decode()

# Example usage (will need dummy model)
if __name__ == "__main__":
    # Dummy model = None
    class DummyModel:
        def get_vpip(self): return 0.2
        def get_pfr(self): return 0.1
        def get_three_bet_freq(self): return 0.05
        def get_fold_to_cbet(self): return 0.4
        def get_range(self):
            # return uniform distribution over a few combos
            combos = [('As','Kh'), ('Qd','Qh'), ('7c','5c')]
            prob = 1.0/len(combos)
            return [(c, prob) for c in combos]
    model = DummyModel()
    board = ['Ah', 'Kd', '9c']
    pot = 6.0
    effective_stack = 20.0
    action_evs = {'fold': 0.0, 'call': 0.2, 'raise_6': 0.35}
    best = 'raise_6'
    hand = ['As', 'Ad']
    print(generate_full_report(model, board, pot, effective_stack,
                               action_evs, best, hand))