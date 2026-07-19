# Archived Assistant

This directory was moved from `poker_assistant/` at the project root.

**Status:** Deprecated. This code has overlapping functionality with `pokerbot_explainable/` and uses a different hand evaluation library (`deuces` instead of `treys`). Retained for reference only.

Key files:
- `opponent_model.py` — Bayesian range estimation (useful concepts)
- `ev_calculator.py` — Monte Carlo EV simulation (has syntax errors)
- `spr_utils.py` — SPR and bet sizing (clean, standalone)
- `explainer.py` — Text report generation
- `preflop.py` — Preflop hand tier advice

If you want to integrate any of these concepts, implement them in `pokerbot_explainable/` using the `treys` library.