# Explainable Poker Bot

A minimalist, debuggable poker bot designed for transparency and iterative improvement.

## Philosophy

- **Explainability First**: Every decision is logged with a complete chain of reasoning
- **Radical Minimalism**: No GUI, no networking, no unnecessary abstractions
- **Modular Design**: Game engine, hand evaluator, and decision maker are strictly decoupled
- **Iterative Upgradability**: Swap decision strategies (heuristics → MCTS → CFR) without touching core logic

## Project Structure

```
pokerbot_explainable/
├── core/                    # Domain logic (immutable, pure functions)
│   ├── game_engine/         # Poker rules, state transitions
│   ├── hand_evaluator/      # Poker hand ranking & board analysis
│   ├── card_utils/          # Card representation, deck utilities
│   └── constants/           # Game constants, hand rankings
├── decision/                # Decision making strategies
│   ├── base/                # Abstract interfaces
│   └── heuristic/           # Initial rule-based implementation
├── explainability/          # Decision tracing & logging systems
├── utils/                   # Cross-cutting utilities
├── config/                  # YAML configuration files
├── tests/                   # Unit tests
└── logs/                    # Decision trace output (JSON)
```

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Run the demo: `python -m pokerbot_explainable.demo`
3. Examine decision traces in `logs/`

## Development Principles

- Never use "black box" logic - every calculation must be traceable
- All configuration externalized (no magic numbers in code)
- Prefer composition over inheritance
- Functions should be pure where possible
- Logging is first-class, not an afterthought
