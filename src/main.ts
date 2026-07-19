import { getAction } from "./ai/ai";
import { getBigBlindValue, getState, isMyTurn, showHandIfPossible } from "./ui";
import { performAction, sanitizeAction, onAction } from "./action";
import { showDebugPanel } from "./debug";
import { Logger } from "./logger";
import { encodeHand } from "./ai/preflopHand";

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
    chrome.storage.local.get(
        [STORAGE_FOLD_KEY],
        (result: { [key: string]: any }) => {
            const stored = result[STORAGE_FOLD_KEY] as string[] | undefined;
            if (Array.isArray(stored))
                setFoldSet(stored);
        },
    );
}

// Refresh settings whenever storage changes (e.g. user clicks in the popup).
chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local")
        return;

    const foldChange = changes[STORAGE_FOLD_KEY];
    if (foldChange && Array.isArray(foldChange.newValue))
        setFoldSet(foldChange.newValue as string[]);
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
    stopBotLoop();

    console.log("starting bot");
    console.log("big blind: " + getBigBlindValue());
    console.log("fold set size: " + getFoldSet().length);

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
        try {
            if (isMyTurn()) {
                console.log("bot turn");

                const state = getState();
                console.log("state: ", state);

                let action: Action | undefined;

                try {
                    action = getAction(state);
                    console.log("bot action:", action);
                }
                catch (err) {
                    action = undefined;
                    console.error("bot action error:", err);
                }

                const sanitizedAction = sanitizeAction(action, state);
                console.log("sanitized bot action:", sanitizedAction);

                logger.log(sanitizedAction, state);

                performAction(sanitizedAction, () => {
                    botLoopTimeout = setTimeout(botLoop, timeoutMs);
                });
            }
            else {
                botLoopTimeout = setTimeout(botLoop, timeoutMs);
            }

            showHandIfPossible();
        }
        catch (err) {
            console.error("bot loop fatal:", err);
            // Always reschedule so the loop survives crashes in getState,
            // DOM access, or any single-tick error.
            botLoopTimeout = setTimeout(botLoop, timeoutMs);
        }
    }

    botLoop();
}

function stopBotLoop() {
    clearTimeout(botLoopTimeout);
    botLoopTimeout = undefined;
    // Reset the beep tracker so the next hand gets a fresh evaluation.
    resetBeepTracker();
}

chrome.runtime.onMessage.addListener((message: ChromeMessage, sender, callback) => {
    switch (message) {
        case "start_bot":
            startBotLoop();
            break;
        case "kill_bot":
            stopBotLoop();
            break;
        case "get_bot_status":
            let status: BotStatus = botLoopTimeout === undefined
                ? "off"
                : "playing"
            ;
            callback(status);
            break;
        case "open_debug":
            showDebugPanel();
            break;
        case "get_debug":
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
    }
});

// Initial settings load (in case the popup is opened after the bot starts).
loadSettings();