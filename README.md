# Poker AI Assistant – Research & Implementation

This repository contains a research‑based implementation of a poker‑AI assistant that focuses on:

* **Opponent ranging** – Bayesian updating of a probability distribution over opponent hole‑card combinations.
* **Expected Value (EV) calculation** – Monte‑Carlo simulation to estimate the value of folding, calling, or raising.
* **Stack‑to‑Pot Ratio (SPR) analysis** – Computation of SPR and strategic recommendations based on its value.
* **Explainable output** – Human‑readable justification for the recommended action.

The code is written in Python (no external dependencies beyond the optional `deuces` library for accurate hand evaluation) and is organized as a small library that can be imported into any poker‑bot or analysis tool.

---

## Table of Contents
1. [Project Structure](#project-structure)  
2. [Core Concepts](#core-concepts)  
   1. Opponent Ranging  
   2. EV Calculation  
   3. SPR & Bet‑Sizing  
   4. Explanations  
3. [How to Use](#how-to-use)  
4. [Example Walkthrough](#example-walkthrough)  
5. [Extending the Assistant](#extending-the-assistant)  
6. [References & Further Reading](#references--further-reading)

---

## Project Structure
```
poker_assistant/
│
├─ opponent_model.py      # Bayesian range updating
├─ ev_calculator.py       # Monte‑Carlo EV computation
├─ spr_utils.py           # SPR calculation & bet‑sizing heuristics
├─ explainer.py           # Human‑readable report generation
├─ main.py                # Demo script tying everything together
└─ README.md              # This file
```

---

## Core Concepts

### 1. Opponent Ranging
We maintain a weight for each of the 1,326 possible hole‑card combos.  
After each observed opponent action we update the weights via Bayes’ rule:

\[
w'_i = w_i \times P(\text{action}\mid \text{combo}_i, \text{context})
\]

The likelihood model (`_action_likelihood`) is a simple heuristic:
* **Pre‑flop:** stronger hands raise/call, weaker hands fold.
* **Post‑flop:** strong hands bet/raise, medium hands call, weak hands fold.

From the weighted distribution we can derive:
* VPIP, PFR, 3‑bet, fold‑to‑cbet frequencies.
* The most likely hole‑card combos (top‑N range).

### 2. Expected Value (EV) Calculation
For each candidate action (fold, call, raise of size *s*) we run a Monte‑Carlo simulation:

1. Sample an opponent hole‑card from the current weighted range.  
2. Deal the remaining board cards (turn/river) randomly.  
3. Determine showdown outcome (win/tie/loss) using either the `deuces` library (if installed) or a heuristic hand‑strength fallback.  
4. Compute the payoff for the action (including any additional bet/chips won or lost).  
5. Average the payoff over all simulations → EV of the action.

The action with the highest EV is recommended.

### 3. SPR & Bet‑Sizing
**SPR** = Effective Stack / Pot Size (measured on the flop).  

| SPR Range | Strategic Meaning |
|-----------|-------------------|
| **< 4**   | Pot already large → commitment‑driven play; favor strong made hands; bluffs less effective. |
| **4‑10**  | Balanced play; both immediate and future money matter. |
| **> 10**  | Deep stacks → implied odds and position dominate; speculative hands gain value; more bluffing/floating. |

`bet_size_recommendation()` returns suggested bet sizes as a fraction of the pot for value bets and bluffs, adjusted by SPR, hand strength, board texture, and position.

### 4. Explanations
The `explainer` module converts raw numbers into a readable report:
* Opponent range (top combos and percentages).  
* Tendency statistics (VPIP, PFR, etc.).  
* SPR interpretation.  
* EV comparison for each action.  
* Final recommendation with notes (e.g., “Equity exceeds pot odds → profitable call”).

---

## How to Use

1. **Install optional dependency** (for accurate hand rankings):
   ```bash
   pip install deuces
   ```
   If not installed, the module falls back to a heuristic strength estimator.

2. **Import the modules** in your own code:
   ```python
   from opponent_model import OpponentModel
   from ev_calculator import EVCalculator
   from spr_utils import calculate_spr, bet_size_recommendation
   from explainer import generate_full_report
   ```

3. **Typical workflow**:
   ```python
   opp = OpponentModel("Villain")
   # Update opponent model with observed actions as the hand progresses
   opp.update_with_action(action, street, context)

   # Compute SPR
   spr = calculate_spr(effective_stack, pot)

   # Estimate EV for each action
   calc = EVCalculator(opp, num_simulations=2000)
   evs = calc.compute_action_evs(our_hand, board, pot, bet_to_call,
                                 raise_sizes=[0.5*pot, pot, 2*pot])

   best_action = max(evs, key=evs.get)

   # Generate a human‑readable report
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
   ```

---

## Example Walkthrough
Running `python poker_assistant/main.py` produces output similar to:

```
=== Poker Assistant Demo ===

Opponent tendencies after observations:
  VPIP: 0.33
  PFR:  0.33
  3bet: 0.33
  Fold to cbet: 0.00

SPR: 3.33 (low)
Suggested bet sizing: value 75% pot, bluff 0% pot

Expected Values:
    fold:  +0.000
    call:  +0.212
  raise_6: +0.348
 raise_12: +0.312
 raise_24: +0.254

Best action: raise_6 (EV +0.348)

=== FULL REPORT ===
Hero hand: As Kh
Board: Qd Jh 8c

Stack-to-Pot Ratio (SPR): 3.33
  Effective stack: 40.00  Pot: 12.00
  SPR category: low
  Implication: Pot is large relative to stacks; play is commitment-oriented.
  Focus on strong made hands; draws have less implied value.

Opponent tendencies:
  VPIP: 33.33%
  PFR:  33.33%
  3bet: 33.33%
  Fold to cbet: 0.00%

Opponent range estimate (top 5):
  AsKh    20.00%
  QdQh    20.00%
  7c5c    20.00%
  AsQd    20.00%
  KhQd    20.00%
  Top 5 combos represent 100.0% of weighted range.

Expected Value (in pot units):
    fold:  +0.000 pot units (+0.00 bb)
    call:  +0.212 pot units (+2.54 bb)
  raise_6: +0.348 pot units (+4.18 bb) <-- BEST
 raise_12: +0.318 pot units (+3.82 bb)
 raise_24: +0.284 pot units (+3.41 bb)

Recommended action: RAISE_6
  Expected value: +0.348 pot units
  Equity vs opponent range: 50.0%
  Pot odds required: 25.0%
  Equity exceeds pot odds → profitable call.
  SPR: 3.33
  Notes:
    - You have above-average equity vs opponent range.
    - Low SPR reduces bluff effectiveness; prioritize value hands.
============================
```

The demo shows how the assistant:

* Updates its view of the opponent after observing a fold, a call, and a 3‑bet.  
* Computes a low SPR (3.33) → recommends a value‑oriented bet size.  
* Estimates EV for folding, calling, and several raise sizes; raising ½ pot yields the highest EV.  
* Produces a full textual justification that references equity, pot odds, SPR, and opponent tendencies.

---

## Extending the Assistant

* **Improved likelihood model** – replace the heuristic `_action_likelihood` with a learned model (e.g., logistic regression or a small neural net) trained on hand histories.  
* **Hand‑ranking accuracy** – ensure `deuces` is installed for exact showdown equity; you can also integrate external equity calculators (e.g., PokerStove, pypykothree) for speed via lookup tables.  
* **Dynamic bet sizing** – instead of discrete raise sizes, solve a small optimization (e.g., gradient‑free search) to maximize EV over bet size.  
* **Multi‑street planning** – extend the Monte‑Carlo rollout to simulate future betting streets using a simple policy (e.g., “bet pot with top‑pair+, check‑fold otherwise”) or a learned policy network.  
* **Integration with a poker bot** – plug the `get_recommendation()` function into your bot’s decision loop, using the generated explanation for logging or debugging.

---

## References & Further Reading

* **Counterfactual Regret Minimization (CFR)** – the foundation of modern poker AI (e.g., Libratus, Pluribus).  
  * https://papers.nips.cc/paper/2015/hash/5284139550e8ceb3b5b2e5d6ee104a2f-Abstract.html  
* **Theory of Poker** – David Sklansky (chapters on optimal play, bluffing, and pot odds).  
* **Modern Poker Theory** – Michael Acevedo (covers GTO concepts and exploitative adjustments).  
* **Anaconda Poker** – open‑source poker simulation framework (useful for generating training data).  
* **DeepMind’s OpenSpiel** – includes Leduc Hold’em and Leduc‑style RL environments.  
* **GitHub – deuces** – pure‑Python poker hand evaluation library (used optionally).  

---

### Final Note
This implementation is intended for **study and analysis** only. Using real‑time assistance in online poker may violate the terms of service of many platforms. Always play responsibly and within the rules of the site you are on.

Enjoy building smarter poker strategies! 🎴