okay, # Poker Bot Auto-Fold Implementation Plan

## Goal
Implement a simple automatic folding mechanism (`AutoFoldAction`) that checks for conditions requiring an immediate fold, and ensures this check is prioritized in the main action decision flow. This fulfills the "TL;DR implement `getAction` function in `src/ai/ai.ts`" requirement found in README.md.

## Prerequisites
*   **Understanding:** The current architectural pattern requires functions to accept a `State` object and return an `Action` object (`Action = { type: string, payload?: any }`).
*   **Dependencies:** Need access to the definitions of `State`, `Action`, and specific enums/types for all modules.

## Plan Steps
1.  **Explore Dependencies (Agent):** Use the `Explore` agent to read relevant types from `src/types.d.ts` and check for existing action handlers in `src/ai/*.ts` to understand the precise structure of `State` and how different actions (`Call`, `Raise`) are defined.
2.  **Create Fold Logic (File Write):** Create a new file, `src/ai/autoFoldLogic.ts`. This file will house the primary logic function:
    *   `calculateFoldAction(state: State): Action`: This function implements simple heuristics for folding (e.g., if current equity is below X%, or pot size delta is too large compared to stack). It must return a standardized `Fold` action object.
3.  **Integrate Logic (File Edit):** Modify `src/ai/ai.ts`. I will locate the main decision block within `getAction` and insert a check: `if (autoFoldLogic.calculateFoldAction(state)) { return foldAction; }`, ensuring this check happens early in the execution flow to prioritize safety over complexity.

## Dependencies and Flow
*   `src/ai/ai.ts` **depends on** `src/ai/autoFoldLogic.ts` (for `calculateFoldAction`).
*   The success of both steps depends on correct definitions found in `src/types.d.ts`.

## Confirmation
This plan systematically addresses the core task by isolating new logic, defining its interfaces, and integrating it into the primary control flow. This sequence minimizes the risk of breaking existing functionality while adding a crucial safety net.