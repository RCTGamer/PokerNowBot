"""
Demo script for the Poker Assistant.
Shows how to use the modules together to get a recommendation and explanation.
Handles both preflop and postflop scenarios.
"""

from opponent_model import OpponentModel
from ev_calculator import EVCalculator
from spr_utils import calculate_spr, bet_size_recommendation
from explainer import generate_full_report
from preflop import preflop_recommendation, explain_preflop

def demo():
    print("=== Poker Assistant Demo ===\n")

    # 1. Create opponent model and update with some observed actions
    opp = OpponentModel("Villain")
    # Simulate observed actions: fold preflop, call flop cbet, 3bet preflop
    opp.update_with_action('fold', 'preflop', {})
    opp.update_with_action('call', 'flop', {'facing_cbet': True})
    opp.update_with_action('raise', 'preflop', {'is_3bet': True})

    print("Opponent tendencies after observations:")
    print(f"  VPIP: {opp.get_vpip():.2f}")
    print(f"  PFR:  {opp.get_pfr():.2f}")
    print(f"  3bet: {opp.get_three_bet_freq():.2f}")
    print(f"  Fold to cbet: {opp.get_fold_to_cbet():.2f}\n")

    # 2. Define hand, board, pot, stacks (example situation)
    our_hand = ['As', 'Kh']          # Ace‑King suited
    board    = ['Qd', 'Jh', '8c']    # Flop: Q-J-8 rainbow
    pot      = 12.0                  # chips already in pot
    bet_to_call = 4.0                # opponent bet 4 into pot of 12
    effective_stack = 40.0           # both players have 40 chips left
    position = 'BU'                  # button / late position
    num_players = 6

    # Determine if we are preflop or postflop
    if len(board) == 0:
        # ---------- PREFLOP ----------
        print("--- PREFLOP SCENARIO ---")
        decision = preflop_recommendation(
            hand=our_hand,
            position=position,
            num_players=num_players,
            effective_stock=effective_stack,
            pot=1.5,                     # SB+BB = 1.5 (assuming SB=0.5, BB=1.0)
            bet_to_call=1.0,             # amount to call (one big blind)
            opponent_model=opp
        )
        print(explain_preflop(decision))
    else:
        # ---------- POSTFLOP ----------
        print("--- POSTFLOP SCENARIO ---")
        # Compute SPR
        spr = calculate_spr(effective_stack, pot)
        print(f"SPR: {spr:.2f} ({'low' if spr < 4 else 'medium' if spr <= 10 else 'high'})")

        # Bet‑sizing recommendation based on SPR and hand strength (we'll estimate hand strength)
        # For demo we use a placeholder hand‑strength estimate; in a real bot you'd compute equity vs range.
        hand_strength_est = 0.65
        rec = bet_size_recommendation(spr, hand_strength=hand_strength_est,
                                      board_texture="medium", position="IP")
        print(f"Suggested bet sizing: value {rec['value_bet']*100:.0f}% pot, "
              f"bluff {rec['bluff bet']*100:.0f}% pot\n")

        # Expected Value calculation for each action
        calc = EVCalculator(opp, num_simulations=2000)
        # Consider a few raise sizes: 0.5*pot, 1*pot, 2*pot
        raise_sizes = [0.5 * pot, 1.0 * pot, 2.0 * pot]
        evs = calc.compute_action_evs(our_hand, board, pot, bet_to_call, raise_sizes)

        print("Expected Values (in chip units):")
        for action, ev in sorted(evs.items(), key=lambda x: x[1], reverse=True):
            print(f"  {action:>8}: {ev: .3f}")
        best_action = max(evs, key=evs.get)
        print(f"\nBest action: {best_action.upper()} (EV {evs[best_action]:.3f})\n")

        # Generate full explanation report
        report = generate_full_report(
            model=opp,
            board=board,
            pot=pot,
            effective_stack=effective_stack,
            action_evs=evs,
            best_action=best_action,
            our_hand=our_hand
        )
        print(report)

if __name__ == "__main__":
    demo()