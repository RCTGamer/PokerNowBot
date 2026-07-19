import { State } from "../state";
import { probabilisticAction, postfixNameToCall, toCallDependent, checkCallBased, uniformFill } from "./probabilisticAction";
import { encodeHand, HAND_VALUES } from "./preflopHand";

/**
 * Preflop hand tiers (0-5, weakest to strongest)
 * Based on standard Texas Hold'em starting hand groupings
 */
export const PREFLOP_TIERS = {
  // Tier 0: Trash hands (almost always fold)
  0: new Set([
    "32o", "32s", "42o", "42s", "43o", "52o", "52s", "53o", "53s", "62o", "62s", "63o", "63s",
    "64o", "64s", "72o", "72s", "73o", "73s", "74o", "74s", "75o", "75s", "82o", "82s",
    "83o", "83s", "84o", "84s", "85o", "85s", "86o", "86s", "92o", "92s", "93o", "93s",
    "94o", "94s", "95o", "95s", "96o", "96s", "97o", "97s", "98o", "98s", "T2o", "T2s",
    "T3o", "T3s", "T4o", "T4s", "T5o", "T5s", "T6o", "T6s", "T7o", "T7s", "T8o", "T8s",
    "T9o", "T9s", "J2o", "J2s", "J3o", "J3s", "J4o", "J4s", "J5o", "J5s", "J6o", "J6s",
    "J7o", "J7s", "J8o", "J8s", "J9o", "J9s", "JTo", "JTs", "Q2o", "Q2s", "Q3o", "Q3s",
    "Q4o", "Q4s", "Q5o", "Q5s", "Q6o", "Q6s", "Q7o", "Q7s", "Q8o", "Q8s", "Q9o", "Q9s",
    "QTo", "QTs", "QJo", "QJs", "K2o", "K2s", "K3o", "K3s", "K4o", "K4s", "K5o", "K5s",
    "K6o", "K6s", "K7o", "K7s", "K8o", "K8s", "K9o", "K9s", "KTo", "KTs", "KJo", "KQs"
  ]),

  // Tier 1: Very weak hands (fold most of the time, occasionally play)
  1: new Set([
    "22", "33", "44", "55", "66", "77", "88", "99", "TT",
    "A2o", "A2s", "A3o", "A3s", "A4o", "A4s", "A5o", "A5s", "A6o", "A6s",
    "A7o", "A7s", "A8o", "A8s", "A9o", "A9s", "ATo", "ATs", "AJo", "AQs",
    "KTs", "KJs", "QJs", "JTs", "T9s", "98s", "87s", "76s", "65s", "54s"
  ]),

  // Tier 2: Weak hands (playable in good position, fold early)
  2: new Set([
    "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AJo", "AQo", "AKo", "KQo", "QJo", "JTo", "T9o", "98o", "87o",
    "76o", "65o", "54o", "43o", "32o",
    "KQo", "QJo", "JTo", "T9o", "98o", "87o", "76o", "65o", "54o", "43o", "32o"
  ]),

  // Tier 3: Playable hands (play in most positions)
  3: new Set([
    "AQ", "AJ", "AT", "KQ", "KJ", "KT", "QJ", "QT", "JT",
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s", "A6s", "A5s", "A4s", "A3s", "A2s",
    "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s", "K5s", "K4s", "K3s", "K2s",
    "QJs", "QTs", "Q9s", "Q8s", "Q7s", "Q6s", "Q5s", "Q4s", "Q3s", "Q2s",
    "JTs", "J9s", "J8s", "J7s", "J6s", "J5s", "J4s", "J3s", "J2s",
    "T9s", "T8s", "T7s", "T6s", "T5s", "T4s", "T3s", "T2s",
    "98s", "97s", "96s", "95s", "94s", "93s", "92s",
    "87s", "86s", "85s", "84s", "83s", "82s",
    "76s", "75s", "74s", "73s", "72s",
    "65s", "64s", "63s", "62s",
    "54s", "53s", "52s",
    "43s", "42s",
    "32s"
  ]),

  // Tier 4: Strong hands (play aggressively)
  4: new Set([
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "77", "66", "55", "44", "33", "22",
    "AK", "AQ", "AJ", "AT", "KQ", "KJ", "KT", "QJ", "QT", "JT",
    "AKs", "AQs", "AJs", "ATs", "A9s", "A8s", "A7s",
    "KQs", "KJs", "KTs", "K9s", "K8s", "K7s", "K6s",
    "QJs", "QTs", "Q9s", "Q8s", "Q7s", "Q6s", "Q5s",
    "JTs", "J9s", "J8s", "J7s", "J6s", "J5s",
    "T9s", "T8s", "T7s", "T6s", "T5s",
    "98s", "97s", "96s", "95s", "94s", "93s",
    "87s", "86s", "85s", "84s", "83s", "82s",
    "76s", "75s", "74s", "73s", "72s",
    "65s", "64s", "63s", "62s",
    "54s", "53s", "52s",
    "43s", "42s",
    "32s"
  ]),

  // Tier 5: Premium hands (always play, often raise/re-raise)
  5: new Set([
    "AA", "KK", "QQ", "JJ", "TT", "AKs", "AQs", "AJs", "AK", "AQ"
  ])
};

/**
 * Get the tier (0-5) for a given hand
 */
export function getHandTier(hand: string): number {
  for (const [tier, hands] of Object.entries(PREFLOP_TIERS)) {
    if (hands.has(hand)) {
      return parseInt(tier);
    }
  }
  // Default to tier 0 if not found (shouldn't happen with complete sets)
  return 0;
}

/**
 * Get position-based hand range adjustments
 * Returns a multiplier for how tight/loose to play based on position
 */
function getPositionMultiplier(position: PositionName, numPlayers: number): number {
  // Position weights: earlier positions = tighter play (lower multiplier)
  const positionWeights: Record<PositionName, number> = {
    'ep': 0.6,   // Early position - tightest
    'mp': 0.8,   // Middle position
    'lp': 1.0,   // Late position - standard
    'dealer': 1.2, // Dealer - loose
    'sb': 0.9,   // Small blind - slightly tight
    'bb': 0.7    // Big blind - tighter (already invested)
  };

  // Table size adjustment: full ring (9-10) = standard, short-handed = looser
  let tableSizeFactor = 1.0;
  if (numPlayers <= 4) {
    tableSizeFactor = 1.3; // Very loose shorthanded
  } else if (numPlayers <= 6) {
    tableSizeFactor = 1.15; // Moderately loose
  } else if (numPlayers >= 9) {
    tableSizeFactor = 0.9; // Tighter full ring
  }

  return (positionWeights[position] || 1.0) * tableSizeFactor;
}

/**
 * Get pot odds adjustment factor
 * Returns a multiplier for calling/raising vs folding based on bet size
 */
function getPotOddsAdjustment(state: State): number {
  const potOdds = state.toCall > 0 ? state.toCall / (state.pot + state.toCall) : 0;

  // If facing a bet, adjust based on pot odds
  if (state.toCall > 0) {
    // Poor pot odds (high bet relative to pot) = more folding
    // Good pot odds (low bet relative to pot) = more calling/raising
    if (potOdds > 0.4) { // Bad pot odds (> 2.5:1 against)
      return 0.6; // Much more likely to fold
    } else if (potOdds > 0.25) { // Medium pot odds (1.5:1 to 2.5:1)
      return 0.8; // Somewhat more likely to fold
    } else if (potOdds > 0.15) { // Decent pot odds (1:1 to 1.5:1)
      return 1.0; // Normal
    } else { // Good pot odds (< 1:1)
      return 1.2; // More likely to call/raise
    }
  }

  // No bet to call - can play more freely
  return 1.1;
}

/**
 * Get base action probabilities for a hand tier and position
 */
function getBaseActionProbs(tier: number, position: PositionName, numPlayers: number): any {
  // Base probabilities for each tier (check/fold, call, minRaise, halfPot, pot, allIn)
  // These are adjusted by position and pot odds later
  const baseProbs: Record<number, any> = {
    0: { // Trash - mostly fold
      checkFoldProbability: 0.85,
      callProbability: 0.10,
      minRaiseProbability: 0.03,
      halfPotRaiseProbability: 0.01,
      potRaiseProbability: 0.005,
      allInProbability: 0.005
    },
    1: { // Weak - mostly fold, sometimes call
      checkFoldProbability: 0.70,
      callProbability: 0.25,
      minRaiseProbability: 0.03,
      halfPotRaiseProbability: 0.01,
      potRaiseProbability: 0.005,
      allInProbability: 0.005
    },
    2: { // Below average - fold/call, rare raise
      checkFoldProbability: 0.50,
      callProbability: 0.40,
      minRaiseProbability: 0.07,
      halfPotRaiseProbability: 0.02,
      potRaiseProbability: 0.008,
      allInProbability: 0.002
    },
    3: { // Playable - balanced
      checkFoldProbability: 0.30,
      callProbability: 0.40,
      minRaiseProbability: 0.15,
      halfPotRaiseProbability: 0.08,
      potRaiseProbability: 0.05,
      allInProbability: 0.02
    },
    4: { // Strong - raise/call, rarely fold
      checkFoldProbability: 0.15,
      callProbability: 0.30,
      minRaiseProbability: 0.25,
      halfPotRaiseProbability: 0.15,
      potRaiseProbability: 0.10,
      allInProbability: 0.05
    },
    5: { // Premium - mostly raise/reraise
      checkFoldProbability: 0.05,
      callProbability: 0.15,
      minRaiseProbability: 0.25,
      halfPotRaiseProbability: 0.20,
      potRaiseProbability: 0.20,
      allInProbability: 0.15
    }
  };

  return baseProbs[tier] || baseProbs[0];
}

/**
 * Main preflop decision function
 */
export function preflopAction(state: State): any {
  // Only active in preflop phase
  if (state.phase.name !== "preflop") {
    return { type: "check_or_fold" }; // Default fold for non-preflop
  }

  // Get hand encoding
  const handKey = encodeHand(state.hand);

  // Get hand tier (0-5)
  const tier = getHandTier(handKey);

  // Get position-based adjustments
  const positionMultiplier = getPositionMultiplier(state.position, state.numPlayers);
  const potOddsAdjustment = getPotOddsAdjustment(state);

  // Get base probabilities for this hand tier
  const baseProbs = getBaseActionProbs(tier, state.position, state.numPlayers);

  // Adjust probabilities based on position and pot odds
  // Higher multiplier = more likely to play (call/raise), lower = more likely to fold
  const adjustedProbs = { ...baseProbs };

  // Apply adjustments: increase call/raise probabilities, decrease fold probability
  const playfulnessFactor = (positionMultiplier + potOddsAdjustment) / 2;

  // Scale down fold probability, scale up call/raise probabilities
  adjustedProbs.checkFoldProbability = Math.max(0.01,
    baseProbs.checkFoldProbability / playfulnessFactor);

  // Distribute the reduced probability to call and raise actions proportionally
  const reducedFold = baseProbs.checkFoldProbability - adjustedProbs.checkFoldProbability;
  const callRaiseTotal = baseProbs.callProbability +
                        baseProbs.minRaiseProbability +
                        baseProbs.halfPotRaiseProbability +
                        baseProbs.potRaiseProbability +
                        baseProbs.allInProbability;

  if (callRaiseTotal > 0) {
    const callRatio = baseProbs.callProbability / callRaiseTotal;
    const minRaiseRatio = baseProbs.minRaiseProbability / callRaiseTotal;
    const halfPotRatio = baseProbs.halfPotRaiseProbability / callRaiseTotal;
    const potRatio = baseProbs.potRaiseProbability / callRaiseTotal;
    const allInRatio = baseProbs.allInProbability / callRaiseTotal;

    adjustedProbs.callProbability = baseProbs.callProbability + (reducedFold * callRatio);
    adjustedProbs.minRaiseProbability = baseProbs.minRaiseProbability + (reducedFold * minRaiseRatio);
    adjustedProbs.halfPotRaiseProbability = baseProbs.halfPotRaiseProbability + (reducedFold * halfPotRatio);
    adjustedProbs.potRaiseProbability = baseProbs.potRaiseProbability + (reducedFold * potRatio);
    adjustedProbs.allInProbability = baseProbs.allInProbability + (reducedFold * allInRatio);
  }

  // Normalize probabilities to sum to 1.0
  const total =
    adjustedProbs.checkFoldProbability +
    adjustedProbs.callProbability +
    adjustedProbs.minRaiseProbability +
    adjustedProbs.halfPotRaiseProbability +
    adjustedProbs.potRaiseProbability +
    adjustedProbs.allInProbability;

  const normalizedProbs = {
    checkFoldProbability: adjustedProbs.checkFoldProbability / total,
    callProbability: adjustedProbs.callProbability / total,
    minRaiseProbability: adjustedProbs.minRaiseProbability / total,
    halfPotRaiseProbability: adjustedProbs.halfPotRaiseProbability / total,
    potRaiseProbability: adjustedProbs.potRaiseProbability / total,
    allInProbability: adjustedProbs.allInProbability / total
  };

  // Use probabilistic action to make the decision
  return probabilisticAction(
    postfixNameToCall("preflop", state),
    state,
    normalizedProbs
  );
}