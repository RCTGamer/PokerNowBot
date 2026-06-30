import { buildHandGrid } from "./handGrid";

const STORAGE_FOLD_KEY = "pokerbot.autofoldHands";
const STORAGE_BEEP_KEY = "pokerbot.beepEnabled";

// Mark in the console + on screen which build is running, so cache issues
// are easy to spot.
const BUILD = "pokerbot v" + chrome.runtime.getManifest().version;
console.log(BUILD);
document.addEventListener("DOMContentLoaded", () => {
    const status = document.getElementById("bot-status");
    if (status)
        status.title = BUILD;
});

function sendMessage(message: ChromeMessage, callback?: (response: any) => void) {
    chrome.tabs.query({currentWindow: true, active: true}, tabs => {
        const currentTabID = tabs.length === 0 ? 0 : tabs[0].id!;
        chrome.tabs.sendMessage(currentTabID, message, callback!);
    });
}

document.getElementById("start-bot")?.addEventListener("click", () => {
    sendMessage("start_bot");
});

document.getElementById("kill-bot")?.addEventListener("click", () => {
    sendMessage("kill_bot");
});

document.getElementById("debug-bot")?.addEventListener("click", () => {
    sendMessage("open_debug");
});

document.getElementById("download-logs")?.addEventListener("click", () => {
    sendMessage("download_logs");
});

/**
 * "Background window" — opens PokerNow in a small dedicated window so the bot
 * keeps running even when the user switches tabs. Chrome aggressively throttles
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
            document.getElementById("bot-status")!.textContent = response;
        });
        sendMessage("get_debug", (response: BotDebug) => {
            const text = response.foldCount === 0 && response.lastBeepKey === null
                ? "—"
                : `folds=${response.foldCount}` +
                  (response.lastFoldKey ? ` last=${response.lastFoldKey}` : "") +
                  (response.lastBeepKey ? ` beep=${response.lastBeepKey}` : "");
            document.getElementById("bot-debug")!.textContent = text;
        });
    },
    500,
);

// ---- Hand grid ----

const gridContainer = document.getElementById("hand-grid")!;
const foldSet = new Set<string>();

function showError(msg: string) {
    console.error(BUILD, msg);
    const grid = document.getElementById("hand-grid");
    if (grid) {
        grid.textContent = msg;
        (grid as HTMLElement).style.color = "#ff8a80";
    }
}

function persistFoldSet() {
    chrome.storage.local.set({ [STORAGE_FOLD_KEY]: Array.from(foldSet) });
}

function renderGrid() {
    try {
        buildHandGrid(gridContainer, foldSet, {
            onToggle: () => persistFoldSet(),
        });
    }
    catch (err) {
        showError("grid render failed: " + (err instanceof Error ? err.message : String(err)));
    }
}

function defaultFoldSet(): string[] {
    // Mirrors DEFAULT_PLAYABLE_HANDS in src/ai/preflopHand.ts — its complement.
    const playable = new Set<string>([
        "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA",
        "AKs", "AKo", "AQs", "AQo", "AJs", "AJo", "ATs", "ATo",
        "KQs", "KQo", "KJs", "KJo",
        "QJs",
        "87s", "76s",
    ]);
    const values = [14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2];
    const valueName = (c: number) => c === 14 ? "A" : c === 13 ? "K" : c === 12 ? "Q" : c === 11 ? "J" : c === 10 ? "T" : String(c);
    const out: string[] = [];
    for (const v of values)
        out.push(valueName(v) + valueName(v));
    for (let i = 0; i < values.length; i++) {
        for (let j = i + 1; j < values.length; j++) {
            out.push(valueName(values[i]) + valueName(values[j]) + "s");
            out.push(valueName(values[i]) + valueName(values[j]) + "o");
        }
    }
    return out.filter(k => !playable.has(k));
}

chrome.storage.local.get(
    [STORAGE_FOLD_KEY, STORAGE_BEEP_KEY],
    (result: { [key: string]: any }) => {
        try {
            const stored = result[STORAGE_FOLD_KEY];
            if (Array.isArray(stored) && stored.length > 0) {
                foldSet.clear();
                for (const k of stored)
                    foldSet.add(k);
            }
            else {
                const defaults = defaultFoldSet();
                foldSet.clear();
                for (const k of defaults)
                    foldSet.add(k);
                chrome.storage.local.set({ [STORAGE_FOLD_KEY]: defaults });
            }
            renderGrid();

            const beepToggle = document.getElementById("beep-toggle") as HTMLInputElement | null;
            if (beepToggle) {
                beepToggle.checked = result[STORAGE_BEEP_KEY] !== false; // default true
                beepToggle.addEventListener("change", () => {
                    chrome.storage.local.set({ [STORAGE_BEEP_KEY]: beepToggle.checked });
                });
            }
        }
        catch (err) {
            showError("popup init failed: " + (err instanceof Error ? err.message : String(err)));
        }
    },
);

// Refresh when storage changes from elsewhere (e.g. main.ts updating beep state).
chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "local")
        return;

    const foldChange = changes[STORAGE_FOLD_KEY];
    if (foldChange && Array.isArray(foldChange.newValue)) {
        const newKeys = foldChange.newValue as string[];
        foldSet.clear();
        for (const k of newKeys)
            foldSet.add(k);
        renderGrid();
    }

    const beepChange = changes[STORAGE_BEEP_KEY];
    if (beepChange && typeof beepChange.newValue === "boolean") {
        const beepToggle = document.getElementById("beep-toggle") as HTMLInputElement | null;
        if (beepToggle) beepToggle.checked = beepChange.newValue;
    }
});

document.getElementById("reset-folds")?.addEventListener("click", () => {
    const defaults = defaultFoldSet();
    foldSet.clear();
    for (const k of defaults)
        foldSet.add(k);
    chrome.storage.local.set({ [STORAGE_FOLD_KEY]: defaults });
    renderGrid();
});