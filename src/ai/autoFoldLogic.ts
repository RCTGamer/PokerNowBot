/**
 * @module autoFoldLogic
 * @description Preflop auto-fold safety net. Folds junk hole cards preflop so the
 * rest of the AI pipeline (ifThenElseAction) only sees hands worth playing.
 *
 * On any post-flop street this returns null — the regular decision flow handles those.
 */

import { PreflopPhase } from "../state";
import { AceCode, KingCode, QueenCode, JackCode } from "../cards";

/**
 * Decide whether the current preflop hand is worth playing.
 *
 * Playable set (conservative):
 *   - Any pair 77+
 *   - AK, AQ, AJ, AT (any suit)
 *   - KQ, KJ (any suit), KJs only
 *   - QJs
 *   - Suited connectors 87s, 76s
 *
 * Everything else is folded. This is intentionally tight; the bot's job here
 * is to not bleed chips on 72o / K2o / etc.
 */
function isPlayablePreflop(hand: Card[]): boolean {
    if (hand.length !== 2) return false;

    const [a, b] = hand;
    const hi = Math.max(a.value.code, b.value.code);
    const lo = Math.min(a.value.code, b.value.code);
    const suited = a.suit === b.suit;
    const paired = hi === lo;

    // Pairs 77 and up.
    if (paired && hi >= 7) return true;

    // Broadways: AK, AQ, AJ, AT.
    if (hi === AceCode && lo >= 10 && lo <= KingCode) return true;

    // KQ, KJ offsuit and suited.
    if (hi === KingCode && (lo === QueenCode || lo === JackCode)) return true;

    // QJ suited only (QJo is marginal, fold).
    if (hi === QueenCode && lo === JackCode && suited) return true;

    // A small set of suited connectors — keep tight.
    if (suited) {
        // 87s, 76s
        if (hi === 8 && lo === 7) return true;
        if (hi === 7 && lo === 6) return true;
    }

    return false;
}

/**
 * Returns a fold action if the current state warrants an immediate auto-fold,
 * otherwise null so the calling AI can proceed with its normal decision flow.
 *
 * Currently only acts preflop. Post-flop decisions are left to ifThenElseAction.
 */
export function calculateFoldAction(state: State): Action | null {
    // Only act preflop — this is an auto-fold-preflop bot.
    if (state.phase.code !== PreflopPhase.code) {
        return null;
    }

    // Defensive: if we somehow don't have two hole cards yet, don't fold.
    if (state.hand.length !== 2) {
        return null;
    }

    if (!isPlayablePreflop(state.hand)) {
        return { type: "check_or_fold" };
    }

    return null;
}