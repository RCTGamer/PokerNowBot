"""
Preflop decision making module.
Provides simple hand‑ranking and position‑based recommendations.
"""

from typing import List, Tuple, Dict, Any

RANKS = '23456789TJQKA'
SUITS = 'shdc'

def hand_to_tuple(hand: List[str]) -> tuple:
    """Convert list like ['As','Kh'] to sorted tuple for consistency."""
    return tuple(sorted(hand))

def is_pair(hand: List[str]) -> bool:
    return hand[0][0] == hand[1][0]

def is_suited(hand: List[str]) -> bool:
    return hand[0][1] == hand[1][1]

def is_connected(hand: List[str]) -> bool:
    """Simple connectivity: gap of 0 or 1 (ignoring suits)."""
    r = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
    v1 = r[hand[0][0]]
    v2 = r[hand[1][0]]
    gap = abs(v1 - v2) - 1  # 0 for connected, -1 for pair, 1 for one‑gap
    return gap <= 1

def hand_strength_tier(hand: List[str]) -> int:
    """
    Return a tier 0-5 (higher = stronger) based on a simplified
    Sklansky‑Malmuth grouping.
    """
    r1, s1 = hand[0][0], hand[0][1]
    r2, s2 = hand[1][0], hand[1][1]
    ranks = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
    v1, v2 = ranks[r1], ranks[r2]
    high = max(v1, v2)
    low = min(v1, v2)
    suited = s1 == s2
    pair = v1 == v2

    # Tier 5: premium
    if pair and high >= 12:                 # QQ+, KK, AA
        return 5
    if high == 14 and low == 13:            # AK
        return 5 if suited else 4

    # Tier 4: strong
    if pair and high >= 10:                 # TT+, JJ
        return 4
    if high == 14 and low >= 10 and suited: # AQs+, AJs
        return 4
    if high == 13 and low == 12 and suited: # KQs
        return 4

    # Tier 3: good
    if pair and high >= 7:                  # 77+, 88, 99
        return 3
    if high == 14 and low >= 8 and suited:  # ATs+, A9s
        return 3
    if high == 13 and low >= 10 and suited: # KTs+, QJs
        return 3
    if high == 12 and low == 11 and suited: # JTs
        return 3
    if suited and abs(v1 - v2) == 1:        # suited connectors
        return 2
    if suited and abs(v1 - v2) == 2:        # suited one‑gap
        return 2

    # Tier 2: playable
    if not suited and high == 14 and low >= 10:   # ATo+, AJo
        return 2
    if not suited and high == 13 and low >= 11:   # KTo+, QJo
        return 2
    if pair and high >= 5:                        # 55+
        return 1
    if suited and (v1 >= 10 or v2 >= 10):         # any ace/king suited
        return 1
    if not suited and high >= 12 and low >= 9:    # broadway offsuit
        return 1

    # Tier 0: marginal / trash
    return 0

def position_factor(position: str, num_players: int) -> float:
    """
    Return a multiplier for how tight/loose to play based on position.
    Earlier position -> lower factor (tighter).
    """
    pos = position.upper()
    if pos in ('UTG', 'EP'):
        base = 0.6
    elif pos in ('MP', 'MIDDLE'):
        base = 0.8
    elif pos in ('CO', 'LP', 'BU'):
        base = 1.0
    elif pos in ('SB', 'BB'):
        base = 0.9
    else:
        base = 0.8
    # Adjust for number of players: full ring (9) tighter, 6max looser
    if num_players <= 6:
        base *= 1.1
    elif num_players >= 9:
        base *= 0.9
    return max(0.3, min(1.5, base))

def stack_factor(effective_stack_bb: float) -> float:
    """
    Adjust aggression based on stack depth (in big blinds).
    Deep stacks (>40bb) -> more room to play, factor >1.
    Short stacks (<15bb) -> push/fold, factor <1.
    """
    if effective_stack_bb >= 40:
        return 1.2
    elif effective_stack_bb >= 20:
        return 1.0
    elif effective_stack_bb >= 10:
        return 0.8
    else:
        return 0.5  # push/fold mode

def preflop_recommendation(
    hand: List[str],
    position: str,
    num_players: int,
    effective_stack: float,
    pot: float,
    bet_to_call: float,
    opponent_model: Any = None
) -> Dict[str, Any]:
    """
    Return a dictionary with suggested action and reasoning.
    """
    # Convert stack to big blinds (assuming the blind unit equals 1.0)
    bb = 1.0
    effective_stack_bb = effective_stack / bb

    tier = hand_strength_tier(hand)
    pos_factor = position_factor(position, num_players)
    stack_factor_val = stack_factor(effective_stack_bb)

    # Effective threshold for action: we divide base thresholds by combined factor.
    # Better position/deep stack => lower threshold => can play weaker hands.
    combined_factor = max(0.3, pos_factor * stack_factor_val)
    base_raise_threshold = 3   # need at least tier 3 to raise in neutral situation
    base_call_threshold = 1    # need at least tier 1 to call

    req_raise = base_raise_threshold / combined_factor
    req_call = base_call_threshold / combined_factor

    # Amount to raise: standard 3bb + extra for callers (we ignore callers for simplicity)
    # If stack is short (<=12bb) we consider shoving instead of raising.
    suggested_amount = None
    action = 'fold'

    if tier >= req_raise:
        if effective_stack_bb <= 12:
            action = 'all_in'
            suggested_amount = effective_stack  # shove all remaining
        else:
            action = 'raise'
            # 3 big blinds + 1 big blind per limper (we assume none)
            suggested_amount = 3.0 * bb
    elif tier >= req_call:
        action = 'call'
        # calling just the bet_to_call
        suggested_amount = bet_to_call
    else:
        action = 'fold'
        suggested_amount = 0.0

    # Build explanation notes
    notes = []
    notes.append(f"Hand tier: {tier} (0=weak, 5=premium)")
    notes.append(f"Position factor: {pos_factor:.2f}")
    notes.append(f"Stack factor ({effective_stack_bb:.1f}bb): {stack_factor_val:.2f}")
    notes.append(f"Combined factor: {combined_factor:.2f}")
    notes.append(f"Required tier to raise: {req_raise:.2f}")
    notes.append(f"Required tier to call: {req_call:.2f}")

    result = {
        'action': action,
        'amount': suggested_amount,
        'hand': hand,
        'position': position,
        'num_players': num_players,
        'effective_stack_bb': effective_stack_bb,
        'hand_tier': tier,
        'notes': notes
    }
    return result

def explain_preflop(decision: Dict[str, Any]) -> str:
    """
    Build a human‑readable explanation from the decision dict.
    """
    lines = []
    lines.append("=== PREFLOP RECOMMENDATION ===")
    lines.append(f"Hand: {''.join(decision['hand'])}")
    lines.append(f"Position: {decision['position']}")
    lines.append(f"Players at table: {decision['num_players']}")
    lines.append(f"Effective stack: {decision['effective_stack_bb']:.1f} bb")
    lines.append("")
    lines.append("Decision factors:")
    for n in decision['notes']:
        lines.append(f"  - {n}")
    lines.append("")
    action = decision['action']
    if action == 'fold':
        lines.append("Recommended action: FOLD")
    elif action == 'call':
        lines.append(f"Recommended action: CALL {decision['amount']:.2f}")
    elif action == 'raise':
        lines.append(f"Recommended action: RAISE to {decision['amount']:.2f}")
    elif action == 'all_in':
        lines.append(f"Recommended action: ALL-IN {decision['amount']:.2f}")
    else:
        lines.append(f"Recommended action: {action.upper()}")
    lines.append("================================")
    return "\n".join(lines)

# Example usage (for quick testing)
if __name__ == "__main__":
    # Dummy opponent model placeholder
    class DummyModel:
        def get_vpip(self): return 0.0
        def get_pfr(self): return 0.0
        def get_three_bet_freq(self): return 0.0
        def get_fold_to_cbet(self): return 0.0
    opp = DummyModel()
    decision = preflop_recommendation(
        hand=['As','Kh'],
        position='BU',
        num_players=6,
        effective_stack=40.0,
        pot=1.5,
        bet_to_call=1.0,
        opponent_model=opp
    )
    print(explain_preflop(decision))