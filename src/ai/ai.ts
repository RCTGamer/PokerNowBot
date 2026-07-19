import { PreflopPhase } from "../state";
import { findBestGapStraight, getPairs, isOneCardFlushPossible, isOneCardStraightPossible, isOpenEndedStraightPresent } from "./aiUtils";
import { ifThenElseAction } from "./ifThenElse/ifThenElseAi";
import { calculateFoldAction } from "./autoFoldLogic";

export function getAction(state: State): Action {
    // Auto-fold logic removed - go straight to standard decision flow

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

    // STANDARD DECISION FLOW
    return ifThenElseAction(state);
}