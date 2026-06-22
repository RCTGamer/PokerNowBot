import { allInRaise, call, canCheck, check, fold, halfPotRaise, minRaise, potRaise, tqPotRaise } from "./ui";

/** Module-level hook so main.ts can react to clicks (e.g. for debug counters). */
type ActionLog = { type: "fold" | "check" | "call" | "raise", key?: string };
let lastAction: ActionLog | null = null;
const actionLogListeners: Array<(a: ActionLog) => void> = [];
export function onAction(listener: (a: ActionLog) => void) {
    actionLogListeners.push(listener);
}
function emitAction(a: ActionLog) {
    lastAction = a;
    for (const l of actionLogListeners) {
        try { l(a); } catch { /* listener errors must not break the click */ }
    }
}
export function getLastAction() { return lastAction; }

export function performAction(action: Action, callback: () => void) {
    if (action.type === "check_or_fold") {
        if (canCheck()) {
            console.log("[pokerbot] -> check() (check_or_fold path, can check)");
            check();
            emitAction({ type: "check" });
        }
        else {
            console.log("[pokerbot] -> fold() (check_or_fold path, cannot check)");
            fold();
            emitAction({ type: "fold" });
        }

        callback?.();
    }
    else if (action.type === "call") {
        call();
        emitAction({ type: "call" });
        callback?.();
    }
    else {
        switch (action.raiseAmount) {
            case "min":
            default:
                minRaise(callback);
                break;
            case "1/2_pot":
                halfPotRaise(callback);
                break;
            // TODO: usare 3/4 pot?
            // case "3/4_pot":
            //     tqPotRaise(callback);
            //     break;
            case "pot":
                potRaise(callback);
                break;
            // TODO: usare overbet?
            case "all_in":
                allInRaise(callback);
                break;
        }
        emitAction({ type: "raise" });
    }
}

export function sanitizeAction(action: Action | undefined, state: State) {
    let sanitized = {...action!};

    switch (sanitized.type) {
        case "check_or_fold":
        case "call":
        case "raise":
            // ok, no problem here
            break;
        default:
            sanitized.type = "check_or_fold";
            break;
    }

    if (sanitized.type === "raise") {
        switch (sanitized.raiseAmount) {
            case "min":
            case "1/2_pot":
            // case "3/4_pot":
            case "pot":
            // case "overbet":
            case "all_in":
                // ok, no problem here
                break;
            default:
                sanitized.raiseAmount = "min";
                break;
        }
    }

    return sanitized;
}