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

const timeoutMs = 500;
const STORAGE_FOLD_KEY = "pokerbot.autofoldHands";
const STORAGE_BEEP_KEY = "pokerbot.beepEnabled";

const logger = new Logger();

let botLoopTimeout: NodeJS.Timer | undefined;
let lastBeepKey: string | null = null;

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

    function botLoop() {
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
                console.error("bot error:", err);
            }

            const sanitizedAction = sanitizeAction(action, state);
            console.log("sanitized bot action:", sanitizedAction);

            // Log the action and state
            logger.log(sanitizedAction, state);

            performAction(sanitizedAction, () => setTimeout(botLoop, timeoutMs));
        }
        else {
            botLoopTimeout = setTimeout(botLoop, timeoutMs);
        }

        showHandIfPossible();
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
const watchIntervalMs = 500;
function preflopWatcher() {
    try {
        const state = getState();
        maybeBeepForHand(state);
    }
    catch {
        // ignore transient DOM errors
    }
}
setInterval(preflopWatcher, watchIntervalMs);