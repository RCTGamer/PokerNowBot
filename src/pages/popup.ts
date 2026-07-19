// Mark in the console + on screen which build is running, so cache issues
// are easy to spot.
const BUILD = "pokerbot v" + chrome.runtime.getManifest().version;
console.log(BUILD);
document.addEventListener("DOMContentLoaded", () => {
    const status = document.getElementById("bot-status");
    if (status)
        status.title = BUILD;
});

/**
 * Send a message to the PokerNow content script.
 *
 * Why this targets `chrome.tabs.query({ url: ... })` instead of
 * `{ currentWindow: true, active: true }`:
 *
 *  - The popup can be opened on a tab/window that is *not* PokerNow
 *    (e.g. the user looked away mid-game). In that case the active tab
 *    has no `chrome.runtime.onMessage` listener, every send fails, and
 *    you get noisy "Could not establish connection" / "Cannot read
 *    properties of undefined (reading 'foldCount')" errors — exactly
 *    what the bug report was.
 *  - The popup's "Background window" button intentionally opens
 *    PokerNow in a small dedicated window so the bot keeps running
 *    even when you switch tabs. The window is intentionally visible from
 *    Chrome's perspective to avoid background-tab throttling; you can
 *    minimize it but keep it open.
 *
 * Why we always supply a callback to `chrome.tabs.sendMessage`:
 *
 *  - With no callback passed, Chrome treats the call as Promise-based.
 *    When the receiver doesn't exist the implicit Promise rejects; with
 *    no `.catch(...)` upstream, that becomes
 *    `popup.html:1 Uncaught (in promise) Error: Could not establish
 *    connection.` A callback converts that failure into a handled
 *    `chrome.runtime.lastError`, which we then swallow.
 */
const TARGET_URLS = [
    "https://www.pokernow.club/*",
    "https://www.pokernow.com/*",
];

function sendMessage(message: ChromeMessage, callback?: (response: any) => void) {
    chrome.tabs.query({ url: TARGET_URLS }, (tabs) => {
        if (chrome.runtime.lastError) {
            console.warn(
                `[pokerbot] tab query failed: ${chrome.runtime.lastError.message}`,
            );
            if (callback) callback(undefined);
            return;
        }
        if (!tabs || tabs.length === 0) {
            // No PokerNow tab open anywhere — silently no-op. Many clicks
            // (start/kill) don't care about a reply; polling callbacks
            // learn "no response yet" and skip the update.
            console.warn(
                "[pokerbot] no tab matches TARGET_URLS; is PokerNow open? host_permissions required in manifest.json.",
            );
            if (callback) callback(undefined);
            return;
        }
        chrome.tabs.sendMessage(tabs[0].id!, message, (response) => {
            if (chrome.runtime.lastError) {
                // Content script may have been unloaded (page navigated,
                // extension reloaded mid-game, etc.). Treat as "no data".
                if (callback) callback(undefined);
                return;
            }
            if (callback) callback(response);
        });
    });
}

document.getElementById("start-bot")?.addEventListener("click", () => {
    sendMessage({ type: "start_bot" });
});

document.getElementById("kill-bot")?.addEventListener("click", () => {
    sendMessage({ type: "kill_bot" });
});

document.getElementById("debug-bot")?.addEventListener("click", () => {
    sendMessage({ type: "open_debug" });
});

document.getElementById("download-logs")?.addEventListener("click", () => {
    sendMessage({ type: "download_logs" });
});

/**
 * "Background window" — opens PokerNow in a small dedicated window so the bot
 * keeps running even when you switch tabs. Chrome aggressively throttles
 * hidden tabs (clamps timers to >=1s and progressively freezes them); a normal
 * window is not classified as a background tab and stays responsive. The user
 * can minimize the window, but must keep it open.
 *
 * type: "normal" — small fixed size keeps it out of the way
 * focused: false — doesn't steal focus from the user's current task
 */
document.getElementById("open-background")?.addEventListener("click", () => {
    chrome.windows.create(
        {
            url: "https://www.pokernow.club",
            type: "normal",
            width: 480,
            height: 720,
            focused: false,
        },
        (win) => {
            if (chrome.runtime.lastError) {
                console.error("[pokerbot] background window failed:", chrome.runtime.lastError.message);
            }
            else if (win) {
                console.log("[pokerbot] background window opened:", win.id);
            }
        },
    );
});

setInterval(
    function uiLoop() {
        sendMessage("get_bot_status", (response: BotStatus) => {
            const statusEl = document.getElementById("bot-status");
            if (!statusEl) return;
            // No PokerNow tab open (manifest missing host_permissions, or
            // the user hasn't opened PokerNow). Show a hint instead of
            // leaving the "off" placeholder — this is the failure mode we
            // just shipped a fix for.
            if (response === undefined) {
                statusEl.textContent = "no game tab";
                return;
            }
            statusEl.textContent = response;
        });
        sendMessage("get_debug", (response: BotDebug) => {
            if (response === undefined) return;
            const text = response.foldCount === 0 && response.lastFoldKey === null
                ? "—"
                : `folds=${response.foldCount}` +
                  (response.lastFoldKey ? ` last=${response.lastFoldKey}` : "");
            document.getElementById("bot-debug")!.textContent = text;
        });
    },
    500,
);