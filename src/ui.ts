import { cardValueCodeFromName, isCardValueCodeValid } from "./cards";
import { parseHandRank } from "./rank";
import { getPhaseFromBoardLength } from "./state";

export function isMyTurn() {
    return document.querySelector(".action-signal") !== null;
}

export function parseCard(element: Element): Card {
    if (!element)
        throw new Error("can't parse card from null element");

    const rawValue = element.querySelector(".value")?.textContent;
    const rawSuit = element.querySelector(".suit")?.textContent;

    if (!rawValue || !rawSuit)
        throw new Error("can't find value or suit in card element");

    const valueName = rawValue as CardValueName;
    const valueCode = cardValueCodeFromName(valueName);

    if (!isCardValueCodeValid(valueCode))
        throw new Error("invalid card value code: " + rawValue);

    return {
        value: {
            name: valueName,
            code: valueCode,
        },
        suit: rawSuit as CardSuit,
    };
}

export function getHandCards() {
    const cards = document.querySelectorAll(".you-player .card");

    try {
        const firstCard = parseCard(cards[0]);
        const secondCard = parseCard(cards[1]);
        return [firstCard, secondCard];
    }
    catch (err) {
        throw new Error("error parsing hand cards: " + err);
    }
}

export function getBoardCards() {
    const cards = [...document.querySelectorAll(".table-cards .card")];

    try {
        return cards.map(parseCard);
    }
    catch (err) {
        throw new Error("error parsing board cards: " + err);
    }
}

export function getBigBlindValue() {
    return parseInt(document.querySelectorAll(".blind-value .chips-value")[1].textContent ?? "");
}

export function getToCallValue() {
    const callText = document.querySelector("button.call")?.textContent;

    if (!callText)
        return 0;

    const lowercasedCallText = callText.toLowerCase();

    if (!lowercasedCallText.includes("call"))
        return 0;

    if (!lowercasedCallText.includes(" "))
        return 0;

    return parseInt(lowercasedCallText.split(" ")[1]);
}

export function getHandRank() {
    const rawRank = document.querySelector(".player-hand-message")?.textContent ?? "";
    return parseHandRank(rawRank);
}

export function getPhase() {
    const boardCardsElements = document.querySelectorAll(".table-cards .card");
    return getPhaseFromBoardLength(boardCardsElements.length);
}

export function getStack() {
    const stackText = document.querySelector(".table-player.you-player .table-player-stack")?.textContent;
    return parseInt(stackText ?? "0");
}

export function getTotalPot() {
    const potText = document.querySelector(".table-pot-size .add-on .chips-value")?.textContent;
    return parseInt(potText ?? "0");
}

export function getPrevPhasePot() {
    const prevPotText = document.querySelector(".table-pot-size .main-value .chips-value")?.textContent;
    return parseInt(prevPotText ?? "0");
}

/**
 * Counts active (non-empty) players at the table.
 * An active player has a name element and/or a non-zero stack.
 */
export function getNumPlayers(): number {
    const players = document.querySelectorAll('.table-player');
    let count = 0;
    for (const p of players) {
        // Skip empty seats
        if (p.classList.contains('empty')) continue;
        const stack = p.querySelector('.table-player-stack');
        const name = p.querySelector('.name, .table-player-name, .player-name');
        if (name && name.textContent && name.textContent.trim().length > 0)
            count++;
        else if (stack && stack.textContent && parseInt(stack.textContent) > 0)
            count++;
    }
    return count || players.length; // fallback: total non-empty elements
}

/**
 * Determines your position relative to the dealer.
 *
 * Scans active (non-empty) player elements in DOM order, finds the dealer
 * chip and your seat, then calculates seats-from-dealer clockwise.
 *
 * @returns PositionName: "ep" | "mp" | "lp" | "dealer" | "sb" | "bb"
 */
export function getPosition(numPlayers: number): PositionName {
    const players = document.querySelectorAll('.table-player');
    let yourIdx = -1;
    let dealerIdx = -1;
    let activeIdx = 0;

    for (const p of players) {
        if (p.classList.contains('empty')) continue;
        const name = p.querySelector('.name, .table-player-name, .player-name');
        const isEmpty = !name || !name.textContent || name.textContent.trim().length === 0;
        if (isEmpty) continue;

        if (p.classList.contains('you-player'))
            yourIdx = activeIdx;

        if (p.querySelector('.dealer-chip, .dealer-button, .dealer'))
            dealerIdx = activeIdx;

        activeIdx++;
    }

    // Fallback if we can't determine position
    if (yourIdx < 0 || dealerIdx < 0 || activeIdx < 2)
        return 'ep';

    // Seats from dealer clockwise (0 = dealer)
    const sfd = (yourIdx - dealerIdx + activeIdx) % activeIdx;

    if (sfd === 0) return 'dealer';
    if (sfd === 1) return 'sb';
    if (sfd === 2) return 'bb';

    const remaining = activeIdx - 3; // seats after blinds

    // Last seat before dealer = cutoff (late position)
    if (sfd === activeIdx - 1) return 'lp';
    // Second-to-last = hijack (late position for our purposes)
    if (remaining >= 4 && sfd === activeIdx - 2) return 'lp';

    // Divide the rest: ~40% early, ~60% middle
    const epCutoff = Math.max(1, Math.floor(remaining * 0.4));
    const rel = sfd - 3; // 0-indexed into non-blind positions

    if (rel < epCutoff) return 'ep';
    return 'mp';
}

export function getState(): State {
    const hand = getHandCards();
    const board = getBoardCards();
    const numPlayers = getNumPlayers();

    return {
        phase: getPhase(),
        handRank: getHandRank(),
        hand,
        board,
        handPlusBoard: [...hand, ...board],
        bigBlind: getBigBlindValue(),
        stack: getStack(),
        pot: getTotalPot(),
        prevPhasePot: getPrevPhasePot(),
        toCall: getToCallValue(),
        position: getPosition(numPlayers),
        numPlayers,
    };
}

export function canCheck() {
    return !document.querySelector<HTMLButtonElement>("button.check")?.disabled;
}

export function check() {
    document.querySelector<HTMLButtonElement>("button.check")?.click();
}

export function fold() {
    document.querySelector<HTMLButtonElement>("button.fold")?.click();
}

export function call() {
    document.querySelector<HTMLButtonElement>("button.call")?.click();
}

function withRaiseMenu(action: () => void) {
    const raiseButton = document.querySelector<HTMLButtonElement>("button.raise")!;

    if (raiseButton.disabled) {
        call();
        action();
        return;
    }

    raiseButton.click();

    setTimeout(
        () => {
            action();
            document.querySelector<HTMLButtonElement>('.raise-controller-form input[type="submit"]')?.click();
        },
        100,
    );
}

function getBetButtons() {
    const buttons = document.querySelectorAll<HTMLButtonElement>(".default-bet-buttons button");
    console.log("bet buttons", buttons);
    return buttons;
}

export function minRaise(callback: () => void) {
    withRaiseMenu(() => {
        getBetButtons()[0]?.click();
        callback?.();
    });
}

export function halfPotRaise(callback: () => void) {
    withRaiseMenu(() => {
        getBetButtons()[1]?.click();
        callback?.();
    });
}

export function tqPotRaise(callback: () => void) {
    withRaiseMenu(() => {
        getBetButtons()[2]?.click();
        callback?.();
    });
}

export function potRaise(callback: () => void) {
    withRaiseMenu(() => {
        getBetButtons()[3]?.click();
        callback?.();
    });
}

export function allInRaise(callback: () => void) {
    withRaiseMenu(() => {
        getBetButtons()[4]?.click();
        callback?.();
    });
}

export function showHandIfPossible() {
    document.querySelector<HTMLButtonElement>('button.show-your-hand')?.click();
}