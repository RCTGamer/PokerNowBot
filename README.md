# PokerNowBot - AI Poker Bot for PokerNow.club

A Chrome extension that plays poker on PokerNow.club automatically, plus a Python-based poker assistant library for opponent modeling and EV calculations.

## Project Structure

```
PokerNowBot/
├── src/                          # TypeScript Chrome Extension
│   ├── main.ts                   # Extension entry point, bot loop
│   ├── ai/
│   │   ├── ai.ts                 # Main AI entry point (preflop auto-fold + postflop logic)
│   │   ├── autoFoldLogic.ts      # Preflop auto-fold + beep notifications
│   │   ├── ifThenElse/           # Rule-based postflop decision engine
│   │   │   ├── ifThenElseAi.ts   # Main decision router by hand rank
│   │   │   ├── preflopActions.ts # Preflop decisions
│   │   │   ├── pairAction.ts     # Pair decisions
│   │   │   ├── twoPairAction.ts  # Two pair decisions
│   │   │   ├── threeAction.ts    # Trips/Set decisions
│   │   │   ├── straightAction.ts # Straight decisions
│   │   │   ├── flushAction.ts    # Flush decisions
│   │   │   ├── highCardAction.ts # High card decisions
│   │   │   └── handActions.ts    # Best hand / bluff actions
│   │   ├── probabilisticAction.ts # Probabilistic action selection
│   │   ├── preflopHand.ts        # Hand encoding (169 canonical hands)
│   │   └── aiUtils.ts            # Hand evaluation utilities
│   ├── logger.ts                 # Chrome extension logger (downloads JSON logs)
│   ├── action.ts                 # Action execution & sanitization
│   ├── ui.ts                     # DOM scraping & state extraction
│   ├── state.ts                  # Game state types
│   ├── rank.ts                   # Hand rank definitions
│   └── types.d.ts                # Type declarations
│
├── poker_assistant/              # Python Poker Assistant Library
│   ├── opponent_model.py         # Bayesian opponent range modeling
│   ├── ev_calculator.py          # Monte Carlo EV calculator
│   ├── spr_utils.py              # SPR & bet sizing utilities
│   ├── explainer.py              # Human-readable explanations
│   ├── preflop.py                # Preflop hand ranking & recommendations
│   └── main.py                   # Demo script
│
├── public/                       # Extension manifest & assets
└── package.json                  # Build config (webpack)
```

---

## Part 1: TypeScript Bot (Chrome Extension)

### How It Works (end-to-end)

```
1. Content script loads on pokernow.club (matches pattern in manifest.json).
2. main.ts loads the user's fold set + beep preference from chrome.storage.local,
   starts the lightweight preflop watcher, and waits for popup messages.
3. User opens the popup, configures their auto-fold grid, optionally clicks
   "background window" to open PokerNow in a small always-visible window
   (so the bot survives background-tab throttling).
4. User clicks "start bot" → main.ts begins a 500ms-tick recursive bot loop.
5. Each tick:
     a. isMyTurn()       — checks PokerNow's .action-signal DOM node
     b. getState()       — scrapes hand, board, pot, stack, etc. from DOM
     c. getAction(state) — routes to auto-fold (Tier 1) or if-then-else (Tier 2)
     d. sanitizeAction() — clamps undefined/invalid actions to safe defaults
     e. logger.log()     — records action + state snapshot in memory
     f. performAction()  — clicks PokerNow's check/fold/call/raise buttons
     g. Self-re-schedules via setTimeout — even if any step throws, the loop
        always reschedules the next tick (resilience, see below).
6. Independently, the preflop watcher fires every ~500ms to beep when a hand
   *outside* the user's fold set appears, even when the bot is stopped —
   so the user hears "you should make a real decision now."
7. The "download logs" button serializes the in-memory log entries to JSON
   and saves to disk via chrome.downloads.
```

The whole bot exists as two tiers of decision logic layered over a DOM scraper and a DOM clicker:

| Layer | What it does | Where |
|---|---|---|
| **DOM scrape** | Read the game state from PokerNow's HTML | `src/ui.ts` |
| **DOM click** | Trigger PokerNow's check/fold/call/raise buttons | `src/action.ts`, `src/ui.ts` |
| **Tier 1: auto-fold** | If preflop + hand is in red cell → fold immediately | `src/ai/autoFoldLogic.ts` |
| **Tier 2: if-then-else** | Otherwise route by hand rank (Pair, Flush…) | `src/ai/ifThenElse/ifThenElseAi.ts` |
| **Probabilistic action** | Mix of fold/call/raise chosen per-tick by random roll | `src/ai/probabilisticAction.ts` |
| **Bot loop / resilience** | Self-healing 500ms tick, always reschedules | `src/main.ts` |
| **Logger** | Records every action + state to in-memory list | `src/logger.ts` |
| **Popup UI** | Red/green fold grid, start/kill/debug/download/bg window | `src/pages/popup.ts`, `src/pages/handGrid.ts` |

---

### Architecture Overview

The TypeScript bot runs as a content script injected into PokerNow pages. It:
1. **Scrapes game state** from the DOM (`ui.ts`)
2. **Runs a bot loop** every 500ms when it's our turn (1000ms when tab is hidden to avoid throttling) (`main.ts`)
3. **Uses a two-tier decision system**:
   - **Tier 1 (Preflop)**: Auto-fold based on user-configured hand grid
   - **Tier 2 (Postflop)**: Rule-based if-then-else logic by hand rank

### Bot Loop Flow (`src/main.ts`)

The bot loop runs on an interval (adaptive based on tab visibility) and follows this flow:

```typescript
botLoop():
  └── 1. Check if it's our turn (isMyTurn())
  └── 2. Scrape game state from DOM (getState())
  └── 3. Get action from AI (getAction())
        ├── Auto-fold check (autoFoldLogic.ts)
        ├── If postflop: log hand strength diagnostics
        └── Delegate to ifThenElseAi.ts
  └── 4. Sanitize the AI action (sanitizeAction())
  └── 5. Log the action + state snapshot (logger.log())
  └── 6. Perform the action / fold (performAction())
```

The logger is called every tick after `sanitizeAction()` — it records the sanitized action, hole cards, board, and pot.

### Visibility-Adaptive Polling

Both the bot loop and the independent preflop watcher adjust their polling interval based on tab visibility:

```typescript
if tab visible    → interval = 500ms  (responsive play)
if tab hidden     → interval = 1000ms (avoids Chrome throttling)
```

A `visibilitychange` listener (`main.ts:updateIntervalsBasedOnVisibility`) dynamically switches the interval when the user switches tabs. The preflop watcher uses **recursive `setTimeout`** rather than `setInterval` so the cadence actually updates when the variable changes (setInterval freezes its period at creation time).

### Running in the Background (Background Window)

Chrome aggressively throttles hidden tabs — clamping `setTimeout`/`setInterval` to ≥1000ms and progressively freezing them. Even at 1000ms, a hidden tab will eventually pause entirely.

To run the bot indefinitely without throttling, the popup has a **"background window"** button (`src/pages/popup.ts`). It opens PokerNow in a small dedicated window via `chrome.windows.create({ type: 'normal', width: 480, height: 720, focused: false })`.

Why this works: Chrome only throttles *hidden tabs*, not separate windows. A minimized/overlapped window is still "visible" from Chrome's perspective, so timers fire at full speed. Minimize the window and leave it open — the bot will keep playing indefinitely.

### Bot Loop Resilience

`botLoop` (`main.ts`) is wrapped in a try/catch that **always reschedules** the next tick, even if state scraping, AI evaluation, or DOM clicks throw. This prevents the loop from silently dying after a transient error (which previously caused the bot to "stop after 3 hands").

The recursive `setTimeout`'s id is always stored in `botLoopTimeout`, so `kill bot` actually stops the loop, even when it is mid-turn.

### Independent Preflop Watcher

In addition to the bot loop, `main.ts` runs a separate `preflopWatcher` interval that fires independently of whether the bot is active:

```
preflopWatcher():
  └── 1. Scrape game state (getState())
  └── 2. Call maybeBeepForHand(state)
        └── playBeepForHand() — beeps once per new hand NOT in the fold set
```

This lets the user hear a beep when they pick up a playable hand even when the bot is stopped, so they can choose to play manually. It also uses the adaptive visibility-based interval (500ms/1000ms).

---

### Tier 1: Preflop Auto-Fold (`src/ai/autoFoldLogic.ts`)

**Core Concept**: 169 canonical preflop hands (13 pairs + 78 suited + 78 offsuit). User configures a "fold set" (red cells in popup grid). Any hand in the fold set → auto-fold preflop. Hands NOT in fold set → beep notification (user makes manual decision).

**Key Functions**:
| Function | Purpose |
|----------|---------|
| `shouldAutoFold(hand: Card[])` | Returns true if hand in fold set |
| `calculateFoldAction(state)` | Returns `{type: "check_or_fold"}` if auto-fold, else `null` |
| `playBeepForHand(state)` | Beeps once per new hand NOT in fold set |
| `setFoldSet(keys)` / `getFoldSet()` | Persist to `chrome.storage.local` |
| `setBeepEnabled(bool)` | Toggle beep notifications |

**Hand Encoding** (`src/ai/preflopHand.ts`):
- 13 pairs: `AA`, `KK`, ..., `22`
- 78 suited: `AKs`, `AQs`, ..., `32s`
- 78 offsuit: `AKo`, `AQo`, ..., `32o`
- Total: 169 canonical hands

**Default Behavior**: Complement of `DEFAULT_PLAYABLE_HANDS` (tight default range)

---

### Tier 2: Postflop If-Then-Else Engine (`src/ai/ifThenElse/ifThenElseAi.ts`)

Routes to hand-specific logic based on `state.handRank`:

```
if preflop          → preflopAction()
else if hand ≥ FH   → bestHandAction()  (value bet/raise)
else
  switch(handRank):
    HighCard    → highCardAction()
    Pair        → pairAction()
    TwoPair     → twoPairAction()
    Trips/Set   → threeAction()
    Straight    → straightAction()
    Flush       → flushAction()
    default     → bluffHandAction()
```

---

### Probabilistic Action System (`src/ai/probabilisticAction.ts`)

All action modules use **probabilistic action selection** for unpredictability:

```typescript
probabilisticAction(name, state, {
  checkFoldProbability: 0.3,
  callProbability: 0.4,
  minRaiseProbability: 0.1,
  halfPotRaiseProbability: 0.1,
  potRaiseProbability: 0.05,
  allInProbability: 0.05
})
```

**Action Types**:
| Key | Action | Amount |
|-----|--------|--------|
| `checkFoldProbability` | `check_or_fold` | - |
| `callProbability` | `call` | - |
| `minRaiseProbability` | `raise` | `"min"` |
| `halfPotRaiseProbability` | `raise` | `"1/2_pot"` |
| `potRaiseProbability` | `raise` | `"pot"` |
| `allInProbability` | `raise` | `"all_in"` |

Probabilities are normalized to sum to 1. Action chosen by random roll.

**Helpers**:
- `toCallDependent(state, {zero, nonZero})` - Different probs when facing bet vs checking
- `checkCallBased({checkFoldProbability, callProbability, ...raiseShares})` - Auto-distributes remainder to raises
- `zeroFill(args)` / `uniformFill(args)` - Fill undefined probabilities

---

### Hand Evaluation Utilities (`src/ai/aiUtils.ts`)

| Function | Purpose |
|----------|---------|
| `isOneCardFlushPossible(handPlusBoard)` | Flush draw detection (1 card suit) |
| `isOpenEndedStraightPresent(cards)` | Open-ended straight draw on board |
| `isOneCardStraightPossible(board)` | Gutshot straight draw detection |
| `findBestGapStraight(board)` | Best possible straight on board |
| `getPairs(cards)` | Pair detection |

---

### Logger (`src/logger.ts`)

**Class**: `Logger` (singleton via `logger.ts` export)

**Features**:
- Logs game state snapshots: timestamp, action, hand, board, pot
- `log(action, state)` - Called on each decision in the bot loop
- `getLogs()` - Retrieve all entries programmatically
- `clear()` - Reset log
- `download(filename?)` - **Downloads JSON log via `chrome.downloads.download()`** (requires `"downloads"` permission in manifest)

**Access via Popup**: The "download logs" button in the extension popup sends a `"download_logs"` message to the content script, which calls `logger.download()`. The file saves as `pokerlog_<timestamp>.json`.

**LogEntry Structure**:
```typescript
interface LogEntry {
  timestamp: number;
  action: {type: string; amount?: number} | null;
  hand: Card[];      // Hole cards
  board: Card[];     // Community cards
  pot?: number;
}
```

**Usage in bot loop** (`main.ts`):
```typescript
import { Logger } from "./logger";
const logger = new Logger();

// ... after sanitizeAction()
logger.log(sanitizedAction, state);
```

**Manifest Requirement** (`public/manifest.json`):
```json
{
  "permissions": ["storage", "downloads"]
}
```

---

### Popup UI (`src/pages/popup.ts` + `handGrid.ts`)

- 169-cell grid (13×13) showing all preflop hands
- **Red** = auto-fold, **Green** = play (beep)
- Click to toggle hands in fold set
- Persists to `chrome.storage.local`
- Debug panel shows fold count, last folded hand, last beeped hand
- **Download logs button** — sends `"download_logs"` message to content script to trigger `logger.download()`
- **Background window button** — opens PokerNow in a small dedicated window via `chrome.windows.create` so the bot runs indefinitely without Chrome's background-tab throttling

---

## Part 2: Python Poker Assistant Library (`poker_assistant/`)

A research-oriented library for opponent modeling, EV calculation, SPR analysis, and explainable recommendations.

### 1. Opponent Modeling (`opponent_model.py`)

**Bayesian Range Updating**: Maintains weight for each of 1,326 hole card combos. Updates via Bayes' rule after each observed action:

```
weight_i ← weight_i × P(action | combo_i, context)
```

**Key Features**:
- `OpponentModel(name)` - Initialize with uniform prior
- `update_with_action(action, street, context)` - Bayesian update
- `get_range()` - Returns normalized `(combo, probability)` list sorted desc
- Heuristic hand strength (`_combo_strength`) based on rank, suitedness, connectivity
- Simple likelihood model: stronger hands more likely to bet/raise, weaker to fold
- Tracks VPIP, PFR, 3-bet%, fold-to-cbet%

**Usage**:
```python
opp = OpponentModel("Villain")
opp.update_with_action('call', 'flop', {'facing_cbet': True})
opp.update_with_action('raise', 'preflop', {'is_3bet': True})
print(f"VPIP: {opp.get_vpip():.2f}")
dist = opp.get_range()  # [(('As','Kh'), 0.004), ...]
```

---

### 2. EV Calculator (`ev_calculator.py`)

**Monte Carlo Simulation** for action EV estimation:

```python
calc = EVCalculator(opponent_model, num_simulations=2000)
evs = calc.compute_action_evs(
    our_hand=['As', 'Ad'],
    board=['Ah', 'Kd', '9c'],
    pot=6.0,
    bet_to_call=2.0,
    raise_sizes=[2.0, 4.0]  # pot/2, pot
)
# Returns: {'fold': 0.0, 'call': 1.5, 'raise_2': 3.2, 'raise_4': 2.8}
```

**Model**:
1. Sample opponent hand from weighted range
2. Deal remaining board cards (turn/river)
3. Determine showdown outcome (uses `deuces` if installed, else heuristic)
4. Compute payoff for fold/call/raise
5. Average over N simulations

**Supports**: `deuces` for exact hand evaluation (pip install deuces)

---

### 3. SPR & Bet Sizing (`spr_utils.py`)

**SPR Calculation**:
```python
spr = calculate_spr(effective_stack=40.0, pot_size=12.0)  # 3.33
```

**SPR Categories**:
| SPR | Category | Strategy |
|-----|----------|----------|
| < 4 | Low | Commitment-driven, value-heavy, bluff less |
| 4-10 | Medium | Balanced, both value & bluff viable |
| > 10 | High | Implied odds, speculative hands, more bluffs |

**Bet Sizing Recommendation**:
```python
rec = bet_size_recommendation(
    spr=3.33,
    hand_strength=0.75,
    board_texture="medium",
    position="IP"
)
# {'value_bet': 0.5, 'bluff_bet': 0.0, 'SPR': 3.33, 'category': 'low'}
```

Adjusts for: SPR, hand strength, board texture (dry/medium/wet), position (IP/OOP)

---

### 4. Explanations (`explainer.py`)

Generates human-readable reports combining all factors:

```python
report = generate_full_report(
    model=opp,
    board=['Qd', 'Jh', '8c'],
    pot=12.0,
    effective_stack=40.0,
    action_evs=evs,
    best_action='raise_6',
    our_hand=['As', 'Kh']
)
```

**Report Sections**:
1. Hero hand & board
2. SPR with strategic implication
3. Opponent tendencies (VPIP, PFR, 3-bet, fold-to-cbet)
4. Top-N weighted opponent combos
5. EV table (fold, call, raise sizes) with BEST highlighted
6. Recommendation with equity, pot odds, SPR notes

---

### 5. Preflop (`preflop.py`)

**Simplified Sklansky-Malmuth Tier (0-5)**:
- Tier 5: AA, KK, QQ, AKs, AKo
- Tier 4: JJ, TT, AQs, AJs, KQs
- Tier 3: 99-77, ATs-A9s, KTs+, QJs, JTs, suited connectors
- Tier 2: AJo+, KQo, 66-55, broadway offsuit
- Tier 1: 44-22, any Ax suited, Kxs, Qxs
- Tier 0: Trash

**Adjustments**:
- Position factor: UTG=0.6, MP=0.8, CO/BU=1.0, SB/BB=0.9 (×1.1 for 6-max, ×0.9 for 9-max)
- Stack factor: ≥40bb=1.2, 20-40bb=1.0, 10-20bb=0.8, <10bb=0.5 (push/fold)

**Thresholds** (divided by combined factor):
- Raise: base tier 3 / factor
- Call: base tier 1 / factor

```python
decision = preflop_recommendation(
    hand=['As', 'Kh'],
    position='BU',
    num_players=6,
    effective_stack=40.0,
    pot=1.5,
    bet_to_call=1.0
)
print(explain_preflop(decision))
# RAISE 3.0 (Tier 4, pos=1.0, stack=1.2, req_raise=2.5, req_call=0.83)
```

---

### Demo (`poker_assistant/main.py`)

```bash
cd poker_assistant
python main.py
```

Shows both preflop and postflop scenarios with full explanation report.

---

## Installation & Usage

### Chrome Extension

```bash
npm install
npm run build
# Load `dist/` folder as unpacked extension in chrome://extensions
```

1. Navigate to `https://www.pokernow.club` and join a table.
2. Re-open the extension's popup (click the toolbar icon).
3. **For long-running background play:** click **"background window"** to open PokerNow in a small dedicated 480×720 window. Chrome throttles hidden tabs aggressively, but not separate windows — so the bot will keep playing indefinitely. Minimize the window and leave it open.
4. Configure your **fold set** in the red/green grid (defaults to a tight range).
5. Click **"start bot"**. The bot will fold anything red, play anything green, and use probabilistic postflop play for hands it gets to play.
6. Click **"download logs"** any time to dump the in-memory session log as JSON.
7. Click **"kill bot"** to stop.

### Python Assistant
```bash
pip install deuces  # optional, for exact equity
cd poker_assistant
python main.py
```

---

## References & Further Reading

- **Counterfactual Regret Minimization (CFR)** - Foundation of modern poker AI (Libratus, Pluribus)
- **The Theory of Poker** - David Sklansky (optimal play, bluffing, pot odds)
- **Modern Poker Theory** - Michael Acevedo (GTO concepts, exploitative adjustments)
- **deuces** - Pure-Python hand evaluation library
- **OpenSpiel** - DeepMind's framework including Leduc Hold'em environments

---

Enjoy building smarter, data-driven poker strategies! ♠️♥️♣️♦️