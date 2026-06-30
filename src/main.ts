import { getAction } from "./ai/ai";
import { getBigBlindValue, getState, isMyTurn, showHandIfPossible } from "./ui";
import { performAction, sanitizeAction, onAction } from "./action";
import { showDebugPanel } from "./debug";
import { Logger } from "./logger";
import {
    setFoldSet,
    shouldAutoFold,
    getFoldSet,
    setBeepEnabled,
    playBeepForHand,
    resetBeepTracker,
} from "./ai/autoFoldLogic";
import { encodeHand } from "./ai/preflopHand";

let timeoutMs = 500;
const STORAGE_FOLD_KEY = "pokerbot.autofoldHands";
const STORAGE_BEEP_KEY = "pokerbot.beepEnabled";

const logger = new Logger();

let botLoopTimeout: NodeJS.Timer | undefined;
let lastBeepKey: string | null = null;
let preflopIntervalId: number;

// --- debug counters exposed to the popup -----------------------------------
let foldCount = 0;
let lastFoldKey: string | null = null;

console.log(`"pokerbot v${chrome.runtime.getManifest().version}"`);

/** Load the fold set and beep toggle from chrome.storage.local. */
function loadSettings() {
    chrome.storage.local.get(
        [STORAGE_FOLD_KEY, STORAGE_BEEP_KEY],
        (result: { [key: string]: any }) => {
            const stored = result[STORAGE_FOLD_KEY] as string[] | undefined;
            if (Array.isArray(stored))
                setFoldSet(stored);

            if (typeof result[STORAGE_BEEP_KEY] === "boolean")
                setBeepEnabled(result[STORAGE_BEEP_KEY]);
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

    const beepChange = changes[STORAGE_BEEP_KEY];
    if (beepChange && typeof beepChange.newValue === "boolean")
        setBeepEnabled(beepChange.newValue);
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

/**
 * Called every tick. The red-vs-green decision and the actual beep live in
 * autoFoldLogic.ts (single source of truth — same set as the popup's hand
 * grid). Here we only record the most recent beeped hand key for the popup's
 * debug counter.
 */
function maybeBeepForHand(state: State) {
    const beepedKey = playBeepForHand(state);
    if (beepedKey !== null) {
        lastBeepKey = beepedKey;
        console.log(`[pokerbot] BEEP (${beepedKey})`);
    }
}

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
                lastBeepKey,
            } satisfies BotDebug);
            break;
        case "download_logs":
            logger.download();
            break;
    }
});

// Initial settings load (in case the popup is opened after the bot starts).
loadSettings();

/**
 * Lightweight preflop watcher — runs whether or not the bot is active so the
 * user hears the beep even when they want to play manually but the bot
 * identified a hand outside their auto-fold set. (i.e. "tell me when I need
 * to make a real decision, but don't auto-fold for me.")
 *
 * Stops as soon as the user closes the bot / page / extension.
 */
function preflopWatcher() {
    try {
        const state = getState();
        maybeBeepForHand(state);
    }
    catch {
        // ignore transient DOM errors
    }
}
// Update timeout intervals based on page visibility to prevent throttling in background tabs
	function updateIntervalsBasedOnVisibility() {
	    if (document.hidden) {
	        // When tab is hidden, use longer intervals to avoid excessive throttling
	        // Use 1000ms (1 second) to stay above Chrome's background tab throttling threshold
	        timeoutMs = 1000;
	    } else {
	        // When tab is visible, use normal responsive interval
	        timeoutMs = 500;
	    }
	}

	// Set initial intervals based on current visibility
	updateIntervalsBasedOnVisibility();

	// Listen for visibility changes to adjust polling intervals
	document.addEventListener('visibilitychange', updateIntervalsBasedOnVisibility);

/**
 * Recursive-setTimeout polling for the preflop watcher, instead of
 * `setInterval`. Reason: setInterval captures its period at creation time,
 * so mutating `timeoutMs` later (as we do on visibilitychange) does NOT
 * change the cadence. Recursive setTimeout reads `timeoutMs` at the moment
 * of rescheduling, so the visibility-based 500ms / 1000ms split actually
 * applies.
 */
function preflopWatcherLoop() {
    preflopWatcher();
    setTimeout(preflopWatcherLoop, timeoutMs);
}
preflopWatcherLoop();