import { PreflopPhase } from "../state";
import { findBestGapStraight, getPairs, isOneCardFlushPossible, isOneCardStraightPossible, isOpenEndedStraightPresent } from "./aiUtils";
import { ifThenElseAction } from "./ifThenElse/ifThenElseAi";
import { calculateFoldAction } from "./autoFoldLogic"; // <-- New import

export function getAction(state: State): Action {
    // 1. HIGH PRIORITY SAFETY CHECK: Auto-fold mechanism
    const foldCheck = calculateFoldAction(state);
    if (foldCheck) {
        return foldCheck;
    }

    // Existing logging and decision flow...
    if (state.phase.code > PreflopPhase.code) {
        console.log("stats", {
            flushDraw: isOneCardFlushPossible(state.handPlusBoard),
            openStraight: isOpenEndedStraightPresent(state.handPlusBoard),
            oneCardFlush: isOneCardFlushPossible(state.board),
            oneCardStraight: isOneCardStraightPossible(state.board),
            bestGapStraight: findBestGapStraight(state.board),
            boardPairs: getPairs(state.board),
        });
    }

    // 2. STANDARD DECISION FLOW
    return ifThenElseAction(state);
}