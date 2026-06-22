/**
 * Preflop hand encoding: maps a 2-card hole hand to one of 169 canonical keys.
 *
 * Keys are strings like "AKs" (suited), "KQo" (offsuit), or "TT" (pair).
 * Order is canonical: the higher value first, then "s" / "o" suffix.
 */

import { AceCode } from "../cards";

/** Card values in display order, high to low. */
export const HAND_VALUES = [14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] as const;
export type HandValueCode = typeof HAND_VALUES[number];

/** Display names for the grid header. 10 is special. */
export function valueCodeToName(code: HandValueCode): string {
    if (code === 14) return "A";
    if (code === 13) return "K";
    if (code === 12) return "Q";
    if (code === 11) return "J";
    if (code === 10) return "T";
    return String(code);
}

/** Encode two cards into a canonical key. Throws if not 2 cards. */
export function encodeHand(cards: Card[]): string {
    if (cards.length !== 2)
        throw new Error("encodeHand expects exactly 2 cards, got " + cards.length);

    const v1 = cards[0].value.code;
    const v2 = cards[1].value.code;
    const suited = cards[0].suit === cards[1].suit;

    const hi = Math.max(v1, v2);
    const lo = Math.min(v1, v2);

    if (hi === lo)
        return valueCodeToName(hi as HandValueCode) + valueCodeToName(lo as HandValueCode);

    return valueCodeToName(hi as HandValueCode) + valueCodeToName(lo as HandValueCode) + (suited ? "s" : "o");
}

/** Returns true if any value in the list equals AceCode. Just a convenience for callers. */
export function isAce(code: number) {
    return code === AceCode;
}

/**
 * Default playable set, mirroring the original hard-coded list in
 * autoFoldLogic.ts so the upgrade is non-breaking.
 *
 * Exported as a hand-key Set so callers can compute its complement.
 */
export const DEFAULT_PLAYABLE_HANDS: ReadonlySet<string> = new Set<string>([
    // Pairs 77+
    "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA",
    // AK, AQ, AJ, AT
    "AKs", "AKo", "AQs", "AQo", "AJs", "AJo", "ATs", "ATo",
    // KQ, KJ offsuit and suited.
    "KQs", "KQo", "KJs", "KJo",
    // QJs
    "QJs",
    // Suited connectors 87s, 76s
    "87s", "76s",
]);