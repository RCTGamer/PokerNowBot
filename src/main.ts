// Content script for the PokerNowBot Chrome extension
import { getAction } from "./ai/ai";
import { getBigBlindValue, getState, isMyTurn, showHandIfPossible } from "./ui";
import { performAction, sanitizeAction, onAction } from "./action";
import { showDebugPanel } from "./debug";
import { Logger } from "./logger";
import { encodeHand } from "./ai/preflopHand";

console.log("Content script loading...");

let timeoutMs = 500;
const STORAGE_FOLD_KEY = "pokerbot.autofoldHands";

const logger = new Logger();

let botLoopTimeout: NodeJS.Timer | undefined;

// --- debug counters exposed to the popup -----------------------------------
let foldCount = 0;
let lastFoldKey: string | null = null;

console.log(`"pokerbot v${chrome.runtime.getManifest().version}"`);

/** Load the fold set from chrome.storage.local. */
function loadSettings() {
    console.log("[Popup] Loading settings..."); // DEBUG
    chrome.storage.local.get(
        [STORAGE_FOLD_KEY],
        (result: { [key: string]: any }) => {
            const stored = result[STORAGE_FOLD_KEY] as string[] | undefined;
            if (Array.isArray(stored)) {
                console.log("[Popup] Settings loaded:", stored.length, "items"); // DEBUG
                setFoldSet(stored);
            } else {
                console.log("[Popup] No stored settings found"); // DEBUG
            }
        },
    );
}

// Refresh settings whenever storage changes (e.g. user clicks in the popup).
chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local") {
        return;
    }

    const foldChange = changes[STORAGE_FOLD_KEY];
    if (foldChange && Array.isArray(foldChange.newValue)) {
        console.log("[Popup] Settings updated:", foldChange.newValue.length, "items"); // DEBUG
        setFoldSet(foldChange.newValue as string[]);
    }
});

// Listen for clicks dispatched by performAction so we can count them.
onAction((a) => {
    if (a.type === "fold") {
        foldCount++;
        // Encode the *current* state.hand so the popup can show "folded 72o".
        // We don't get the hand key from the action itself; grab it lazily.
        try {
            const st = getState();
            if (st.hand.length === 2) {
                lastFoldKey = encodeHand(st.hand);
            }
        }
        catch { /* DOM not ready, leave lastFoldKey as-is */ }
        console.log(`[pokerbot] FOLD #${foldCount} (${lastFoldKey ?? "?"})`);
    }
});

function startBotLoop() {
    console.log("[Popup] startBotLoop called"); // DEBUG
    stopBotLoop();

    console.log("starting bot");
    try {
        console.log("big blind: " + getBigBlindValue());
    }
    catch (e) {
        console.error("Error getting big blind:", e);
    }
    try {
        console.log("fold set size: " + getFoldSet().length);
    }
    catch (e) {
        console.error("Error getting fold set size:", e);
    }

    /**
     * Self-healing bot loop:
     *  - Always reschedules the next tick in a finally-like style so any
     *    error in state scraping / action selection / DOM clicks doesn't
     *    silently kill the loop (this was the "stops after 3 hands" bug).
     *  - Always stores the next setTimeout id in botLoopTimeout so
     *    stopBotLoop can actually stop the loop, even when it is mid-turn.
     *  - Reads timeoutMs at the moment of rescheduling so the
     *    visibility-based interval change takes effect on the next tick.
     */
    function botLoop() {
        let actionTaken = false;
        try {
            if (isMyTurn()) {
                console.log("[Popup] bot turn"); // DEBUG

                let state: State;
                try {
                    state = getState();
                    console.log("[Popup] state:", state); // DEBUG
                }
                catch (e) {
                    console.error("[Popup] Error getting state:", e);
                    // Continue to reschedule loop
                    botLoopTimeout = setTimeout(botLoop, timeoutMs);
                    return;
                }

                let action: Action | undefined;

                try {
                    action = getAction(state);
                    console.log("[Popup] bot action:", action); // DEBUG
                }
                catch (err) {
                    action = undefined;
                    console.error("[Popup] Bot action error:", err);
                }

                let sanitizedAction: Action | undefined = undefined;
                try {
                    sanitizedAction = sanitizeAction(action, state);
                    console.log("[Popup] sanitized bot action:", sanitizedAction); // DEBUG
                }
                catch (e) {
                    console.error("[Popup] Error sanitizing action:", e);
                    // Continue with original action or undefined
                    sanitizedAction = action;
                }

                try {
                    logger.log(sanitizedAction, state);
                    console.log("[Popup] Action logged"); // DEBUG
                }
                catch (e) {
                    console.error("[Popup] Error logging action:", e);
                }

                try {
                    performAction(sanitizedAction, () => {
                        botLoopTimeout = setTimeout(botLoop, timeoutMs);
                        actionTaken = true;
                    });
                }
                catch (e) {
                    console.error("[Popup] Error performing action:", e);
                    // Still reschedule on error
                    botLoopTimeout = setTimeout(botLoop, timeoutMs);
                }
            }
            else {
                // Not our turn
                botLoopTimeout = setTimeout(botLoop, timeoutMs);
                actionTaken = true; // Consider scheduling as "taken" action
            }

            try {
                showHandIfPossible();
            }
            catch (e) {
                console.error("[Popup] Error showing hand:", e);
            }
        }
        catch (err) {
            console.error("[Popup] Bot loop fatal:", err);
            // Always reschedule so the loop survives crashes in getState,
            // DOM access, or any single-tick error.
            botLoopTimeout = setTimeout(botLoop, timeoutMs);
        }

        // Debug: let us know if no action was taken in this iteration
        if (!actionTaken) {
            console.log("[Popup] No action taken in this loop iteration");
        }
    }

    console.log("[Popup] Starting bot loop"); // DEBUG
    botLoop();
}

function stopBotLoop() {
    console.log("[Popup] stopBotLoop called"); // DEBUG
    if (botLoopTimeout !== undefined) {
        clearTimeout(botLoopTimeout);
        botLoopTimeout = undefined;
    }
    // Reset the beep tracker so the next hand gets a fresh evaluation.
    try {
        resetBeepTracker();
    }
    catch (e) {
        console.error("[Popup] Error resetting beep tracker:", e);
    }
}

chrome.runtime.onMessage.addListener((message: any, sender, callback) => {
    console.log("[Popup] Received message:", message); // DEBUG
    if (message && message.type) {
        switch (message.type) {
            case "start_bot":
                console.log("[Popup] Starting bot loop from message"); // DEBUG
                startBotLoop();
                break;
            case "kill_bot":
                console.log("[Popup] Stopping bot from message"); // DEBUG
                stopBotLoop();
                break;
            case "get_bot_status":
                let status: BotStatus = botLoopTimeout === undefined
                    ? "off"
                    : "playing"
                ;
                console.log("[Popup] Returning status:", status); // DEBUG
                callback(status);
                break;
            case "open_debug":
                console.log("[Popup] Opening debug panel"); // DEBUG
                showDebugPanel();
                break;
            case "get_debug":
                console.log("[Popup] Returning debug info"); // DEBUG
                callback({
                    foldCount,
                    lastFoldKey,
                } satisfies BotDebug);
                break;
            case "download_logs":
                // MV3: chrome.downloads is undefined inside content scripts
                // (only the service worker has it). So we serialize the logs
                // here and forward to background.ts, which performs the actual
                // download via a data: URL (see [[chrome-mv3-service-worker-blob-urls]]).
                console.log("[Popup] Handling download_logs request"); // DEBUG
                chrome.runtime.sendMessage(
                    {
                        type: "download_logs",
                        data: JSON.stringify(logger.getLogs(), null, 2),
                        filename: `pokerlog_${Date.now()}.json`,
                    },
                    (response:
                        | { ok: true; downloadId: number }
                        | { error: string }
                        | undefined) => {
                        if (chrome.runtime.lastError) {
                            console.error(
                                "[pokerbot] download_logs dispatch failed:",
                                chrome.runtime.lastError.message,
                            );
                            return;
                        }
                        if (!response) {
                            console.error(
                                "[pokerbot] download_logs: no listener responded (is background.ts registered?)",
                            );
                            return;
                        }
                        if ("error" in response) {
                            console.error("[pokerbot] download_logs:", response.error);
                        }
                        // success: nothing to do; the save dialog appeared in
                        // the user's downloads flow.
                    },
                );
                break;
            default:
                console.warn("[Popup] Unknown message type received:", message.type); // DEBUG
        }
    } else {
        console.warn("[Popup] Received invalid message:", message);
    }
    // Return true to indicate we will respond asynchronously (if we do)
    return true;
});

// Initial settings load (in case the popup is opened after the bot starts).
loadSettings();