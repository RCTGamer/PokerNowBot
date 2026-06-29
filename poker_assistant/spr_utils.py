"""
Stack-to-Pot Ratio (SPR) utilities.
Provides SPR calculation and bet sizing recommendations based on SPR and hand strength.
"""

from typing import Tuple, Dict

def calculate_spr(effective_stack: float, pot_size: float) -> float:
    """
    Compute Stack-to-Pot Ratio.
    :param effective_stack: smaller of the two players' remaining stacks
    :param pot_size: current pot size (including bets already in pot)
    :return: SPR = effective_stack / pot_size
    """
    if pot_size == 0:
        return float('inf')
    return effective_stack / pot_size

def spr_category(spr: float) -> str:
    """
    Categorize SPR into strategic zones.
    """
    if spr < 4:
        return "low"
    elif spr <= 10:
        return "medium"
    else:
        return "high"

def bet_size_recommendation(spr: float,
                            hand_strength: float,  # 0-1, where 1 is nuts
                            board_texture: str = "medium",  # dry, medium, wet
                            position: str = "IP") -> Dict[str, float]:
    """
    Suggest bet sizes for value and bluff based on SPR, hand strength, texture, position.
    Returns dict with recommended bet sizes as fraction of pot.
    """
    # Base fractions
    if spr < 4:  # low SPR -> polarized or value-heavy
        if hand_strength > 0.85:  # near nuts
            value_frac = 0.75  # large bet for value
            bluff_frac = 0.0   # bluff less effective
        elif hand_strength > 0.6:  # medium strong
            value_frac = 0.5
            bluff_frac = 0.0
        else:
            value_frac = 0.0
            bluff_frac = 0.0  # check/fold
    elif spr <= 10:  # medium SPR
        if hand_strength > 0.85:
            value_frac = 0.6
            bluff_frac = 0.4
        elif hand_strength > 0.6:
            value_frac = 0.5
            bluff_frac = 0.3
        else:
            value_frac = 0.0
            bluff_frac = 0.2  # occasional bluff
    else:  # high SPR -> more room for implied odds, larger bets for value, more bluffs
        if hand_strength > 0.85:
            value_frac = 0.8
            bluff_frac = 0.5
        elif hand_strength > 0.6:
            value_frac = 0.6
            bluff_guess = 0.4
        else:
            value_frac = 0.0
            bluff_frac = 0.3

    # Adjust for board texture (wet boards -> smaller value bets, larger bluffs?)
    texture_factor = {"dry": 1.2, "medium": 1.0, "wet": 0.8}
    factor = texture_factor.get(board_texture, 1.0)
    value_frac *= factor
    bluff_frac *= factor

    # Position play: out of position may bet smaller for control
    if position == "OOP":
        value_frac *= 0.8
        bluff_frac *= 0.8

    # Clamp to reasonable range
    value_frac = max(0.0, min(2.0, value_frac))
    bluff_frac = max(0.0, min(2.0, bluff_frac))

    return {
        "value_bet": value_frac,
        "bluff bet": bluff_frac,
        "SPR": spr,
        "category": spr_category(spr)
    }

def spr_based_action_suggestion(spr: float,
                                hand_strength: float,
                                ev_call: float,
                                ev_raise: float,
                                ev_fold: float = 0.0) -> str:
    """
    Simple recommendation based on EV and SPR.
    """
    best_action = max([('fold', ev_fold), ('call', ev_call), ('raise', ev_raise)], key=lambda x: x[1])[0]
    # Adjust based on SPR heuristics
    if spr < 4 and hand_strength < 0.5 and best_action != 'fold':
        # In low SPR, weak hands should often fold
        return 'fold'
    if spr > 10 and hand_strength > 0.8 and best_action == 'fold':
        # Deep stacks, strong hand, consider raising for value
        return 'raise'
    return best_action

# Example usage
if __name__ == "__main__":
    spr = calculate_spr(effective_stack=15.0, pot_size=5.0)
    print(f"SPR: {spr:.2f} -> {spr_category(spr)}")
    rec = bet_size_recommendation(spr, hand_strength=0.78, board_texture="dry", position="IP")
    print("Bet sizing recommendation:", rec)