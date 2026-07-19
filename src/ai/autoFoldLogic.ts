/**
 * @module autoFoldLogic
 * @description Manages the fold set for preflop hands. The beep and auto-fold
 * functionality has been removed as part of the preflop strategy rebuild.
 */

import { PreflopPhase } from "../state";
import { encodeHand, DEFAULT_PLAYABLE_HANDS } from "./preflopHand";

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
 * Replace the in-memory fold set. Called by popup.ts on startup and on
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
 * Returns true if the given hand should be considered for folding preflop.
 * Always returns false outside the preflop phase.
 *
 * Note: This function is kept for compatibility but always returns false
 * since auto-fold logic has been removed from the decision flow.
 */
export function shouldAutoFold(hand: Card[]): boolean {
    // Auto-fold logic removed - always return false
    return false;
}

/**
 * Returns null since auto-fold action has been removed.
 * Kept for compatibility with any remaining imports.
 */
export function calculateFoldAction(state: State): null {
    return null;
}

/**
 * Sets the beep-enabled flag. Kept for compatibility but beep functionality
 * has been removed.
 */
export function setBeepEnabled(enabled: boolean) {
    // Beep functionality removed
}

/**
 * Resets the beep tracker. Kept for compatibility.
 */
export function resetBeepTracker() {
    // Beep functionality removed
}

/**
 * Returns null since beep functionality has been removed.
 * Kept for compatibility.
 */
export function playBeepForHand(state: State): null {
    return null;
}