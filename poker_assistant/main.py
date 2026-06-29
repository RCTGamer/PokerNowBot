"""
Demo script for the Poker Assistant.
Shows how to use the modules together to get a recommendation and explanation.
"""

from opponent_model import OpponentModel
from ev_calculator import EVCalculator
from spr_utils import calculate_spr, bet_size_recommendation
from explainer import generate_full_report

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
    effective_stack = 40.0           # both players have ~40 left

    # 3. Compute SPR
    spr = calculate_spr(effective_stack, pot)
    print(f"SPR: {spr:.2f} ({'low' if spr < 4 else 'medium' if spr <= 10 else 'high'})")

    # 4. Bet‑sizing recommendation based on SPR and hand strength (we'll estimate hand strength)
    # For demo we'll just call the function with a placeholder hand strength estimate
    # In practice you'd compute equity vs range; here we use 0.65 as an example.
    rec = bet_size_recommendation(spr, hand_strength=0.65,
                                  board_texture="medium", position="IP")
    print(f"Suggested bet sizing: value {rec['value_bet']*100:.0f}% pot, "
          f"bluff {rec['bluff bet']*100:.0f}% pot\n")

    # 5. Expected Value calculation for each action
    calc = EVCalculator(opp, num_simulations=2000)  # increase for more accuracy
    # Consider a few raise sizes: 0.5*pot, 1*pot, 2*pot
    raise_sizes = [0.5 * pot, 1.0 * pot, 2.0 * pot]
    evs = calc.compute_action_evs(our_hand, board, pot, bet_to_call, raise_sizes)

    print("Expected Values (in chip units):")
    for action, ev in sorted(evs.items(), key=lambda x: x[1], reverse=True):
        print(f"  {action:>8}: {ev: .3f}")
    best_action = max(evs, key=evs.get)
    print(f"\nBest action: {best_action.upper()} (EV {evs[best_action]:.3f})\n")

    # 6. Generate full explanation report
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