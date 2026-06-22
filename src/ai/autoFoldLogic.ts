/**
 * @module autoFoldLogic
 * @description Preflop auto-fold + soft "your-turn" beep. The two decisions
 * for a NEW preflop hand are co-located here so the popup's red/green grid is
 * the single source of truth:
 *
 *   - hand key is in `foldSet` (red cell)  → auto-fold on the bot's turn
 *   - hand key is NOT in `foldSet` (green) → call playBeep() once so the user
 *                                            knows to make a manual decision
 *
 * The fold set is stored in module state, refreshed by main.ts when
 * chrome.storage.local changes. The beep volume is owned by beep.ts.
 *
 * On any post-flop street this module is a no-op — the regular decision flow
 * handles those.
 */

import { PreflopPhase } from "../state";
import { encodeHand, DEFAULT_PLAYABLE_HANDS } from "./preflopHand";
import { playBeep } from "../beep";

/**
 * Enumerates all 169 canonical preflop hands. Order:
 *   - 13 pairs (AA, KK, … 22)
 *   - 78 suited combinations
 *   - 78 offsuit combinations
 */
export const ALL_HANDS: readonly string[] = enumerateAllHands();

function enumerateAllHands(): readonly string[] {
    const out: string[] = [];
    const values = [14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2];

    for (const v of values)
        out.push(valueToName(v) + valueToName(v)); // pairs

    for (let i = 0; i < values.length; i++) {
        for (let j = i + 1; j < values.length; j++) {
            const hi = values[i];
            const lo = values[j];
            out.push(valueToName(hi) + valueToName(lo) + "s");
            out.push(valueToName(hi) + valueToName(lo) + "o");
        }
    }

    return out;
}

function valueToName(code: number): string {
    if (code === 14) return "A";
    if (code === 13) return "K";
    if (code === 12) return "Q";
    if (code === 11) return "J";
    if (code === 10) return "T";
    return String(code);
}

/**
 * The set of preflop hands to auto-fold, keyed by their canonical name
 * (e.g. "AKo", "TT", "76s"). Refreshed via setFoldSet().
 *
 * Initialized to the complement of DEFAULT_PLAYABLE_HANDS so the bot behaves
 * the same as the pre-upgrade version out of the box.
 */
let foldSet: Set<string> = new Set(
    ALL_HANDS.filter(k => !DEFAULT_PLAYABLE_HANDS.has(k)),
);

/**
 * Replace the in-memory fold set. Called by main.ts on startup and on
 * chrome.storage changes.
 */
export function setFoldSet(keys: Iterable<string>) {
    foldSet = new Set(keys);
}

/**
 * Returns the current fold set as an array (for persistence to storage).
 */
export function getFoldSet(): string[] {
    return Array.from(foldSet);
}

/**
 * Returns true if the given hand should be auto-folded preflop.
 * Always returns false outside the preflop phase.
 */
export function shouldAutoFold(hand: Card[]): boolean {
    if (hand.length !== 2) return false;
    return foldSet.has(encodeHand(hand));
}

/**
 * Returns a fold action if the current state warrants an immediate auto-fold,
 * otherwise null so the calling AI can proceed with its normal decision flow.
 */
export function calculateFoldAction(state: State): Action | null {
    // Only act preflop — this is an auto-fold-preflop bot.
    if (state.phase.code !== PreflopPhase.code) {
        return null;
    }

    if (state.hand.length !== 2) {
        return null;
    }

    if (shouldAutoFold(state.hand)) {
        return { type: "check_or_fold" };
    }

    return null;
}

// ---------------------------------------------------------------------------
// Beep
// ---------------------------------------------------------------------------

/**
 * Tracks the hand key we last evaluated so we don't beep on every 500ms tick
 * while the user stares at the same hole cards. Reset by `resetBeepTracker()`
 * when the bot stops (or on first call).
 */
let lastBeepedHandKey: string | undefined;

/**
 * Toggled by main.ts in response to the popup's "beep on hands you play"
 * checkbox. Defaults to true to match the previous main.ts behaviour.
 */
let beepEnabled = true;

/** Replace the in-memory beep-enabled flag. Called by main.ts on storage changes. */
export function setBeepEnabled(enabled: boolean) {
    beepEnabled = !!enabled;
}

/** Forget the last hand key we beeped for. Call when the bot stops. */
export function resetBeepTracker() {
    lastBeepedHandKey = undefined;
}

/**
 * On each tick, when a NEW preflop hand appears, decide once:
 *   - red  (hand in fold set)  → silence (the bot will auto-fold; see
 *                                 calculateFoldAction). The popup calls the
 *                                 fold button via performAction().
 *   - green (hand NOT in fold set) → call playBeep() once so the user knows
 *                                     to make a manual decision.
 *
 * "New" is defined as a hand key that differs from the last one we evaluated,
 * so re-ticks of the same hand don't re-beep.
 *
 * @returns the hand key that was beeped for, or null if no beep was played.
 */
export function playBeepForHand(state: State): string | null {
    if (!beepEnabled)
        return null;

    if (state.phase.code !== PreflopPhase.code)
        return null;
    if (state.hand.length !== 2)
        return null;

    const handKey = encodeHand(state.hand);

    if (handKey === lastBeepedHandKey)
        return null;
    lastBeepedHandKey = handKey;

    if (shouldAutoFold(state.hand))
        return null; // red cell → bot will fold; stay silent

    playBeep();
    return handKey;
}