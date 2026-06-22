/**
 * Debug panel: injected onto the PokerNow page to manually verify that
 *   1. card/state parsing (the readers in ui.ts) returns the right values, and
 *   2. action clicks (fold / call / check / raises) actually do something.
 *
 * Every read and every click goes through the same functions the bot uses
 * (imported from ./ui), so if the bot stops working the panel will too —
 * which is the point: they share one code path.
 */

import {
    getBoardCards,
    getHandCards,
    getHandRank,
    getPhase,
    getStack,
    getTotalPot,
    getPrevPhasePot,
    getToCallValue,
    getBigBlindValue,
    isMyTurn,
    canCheck,
    fold,
    call,
    check,
    minRaise,
    halfPotRaise,
    potRaise,
    allInRaise,
} from "./ui";

const PANEL_ID = "pokerbot-debug-panel";
const STYLE_ID = "pokerbot-debug-panel-style";
const REFRESH_MS = 500;

let panelRoot: HTMLDivElement | undefined;
let refreshTimer: number | undefined;

export function showDebugPanel() {
    if (panelRoot) {
        // already injected — just bring it to the front
        panelRoot.style.display = "block";
        return;
    }

    injectStyle();
    panelRoot = buildPanel();
    document.body.appendChild(panelRoot);

    refreshTimer = window.setInterval(refreshPanel, REFRESH_MS);
    refreshPanel();
}

function hideDebugPanel() {
    if (refreshTimer !== undefined) {
        clearInterval(refreshTimer);
        refreshTimer = undefined;
    }
    panelRoot?.remove();
    panelRoot = undefined;
}

function injectStyle() {
    if (document.getElementById(STYLE_ID))
        return;

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
        #${PANEL_ID} {
            position: fixed;
            top: 12px;
            right: 12px;
            width: 360px;
            max-height: 90vh;
            overflow-y: auto;
            z-index: 99999;
            background: #1e1e1e;
            color: #e0e0e0;
            font: 12px/1.4 ui-monospace, Menlo, Consolas, monospace;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px 12px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        }
        #${PANEL_ID} .pdb-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            border-bottom: 1px solid #333;
            padding-bottom: 6px;
        }
        #${PANEL_ID} .pdb-title { font-weight: bold; }
        #${PANEL_ID} .pdb-close {
            background: #444; color: #e0e0e0; border: none;
            padding: 2px 8px; border-radius: 3px; cursor: pointer;
        }
        #${PANEL_ID} .pdb-section {
            margin-top: 8px;
            padding-top: 6px;
            border-top: 1px solid #2a2a2a;
        }
        #${PANEL_ID} .pdb-section:first-of-type { border-top: none; }
        #${PANEL_ID} .pdb-row {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            padding: 2px 0;
        }
        #${PANEL_ID} .pdb-label { color: #888; }
        #${PANEL_ID} .pdb-raw { color: #6a9fb5; font-size: 10px; }
        #${PANEL_ID} .pdb-parsed { color: #c8e6c9; }
        #${PANEL_ID} .pdb-err { color: #ef9a9a; }
        #${PANEL_ID} .pdb-turn-yes { color: #a5d6a7; font-weight: bold; }
        #${PANEL_ID} .pdb-turn-no  { color: #888; }
        #${PANEL_ID} .pdb-buttons {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 4px;
            margin-top: 6px;
        }
        #${PANEL_ID} .pdb-buttons button {
            background: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 6px 4px;
            cursor: pointer;
            font: inherit;
        }
        #${PANEL_ID} .pdb-buttons button:hover { background: #3d3d3d; }
        #${PANEL_ID} .pdb-buttons button:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }
        #${PANEL_ID} .pdb-refresh {
            margin-top: 8px;
            width: 100%;
            background: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 6px;
            cursor: pointer;
            font: inherit;
        }
        #${PANEL_ID} .pdb-cards {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        #${PANEL_ID} .pdb-card {
            background: #2a2a2a;
            border: 1px solid #444;
            border-radius: 3px;
            padding: 3px 6px;
        }
        #${PANEL_ID} .pdb-card .pdb-raw { display: block; margin-top: 2px; }
    `;
    document.head.appendChild(style);
}

function buildPanel(): HTMLDivElement {
    const root = document.createElement("div");
    root.id = PANEL_ID;

    root.innerHTML = `
        <div class="pdb-header">
            <span class="pdb-title">PokerBot debug</span>
            <button class="pdb-close" data-action="close">close</button>
        </div>

        <div class="pdb-section">
            <div class="pdb-row">
                <span class="pdb-label">your turn?</span>
                <span data-bind="myTurn">–</span>
            </div>
            <div class="pdb-row">
                <span class="pdb-label">phase</span>
                <span data-bind="phase">–</span>
            </div>
            <div class="pdb-row">
                <span class="pdb-label">hand rank</span>
                <span data-bind="handRank">–</span>
            </div>
            <div class="pdb-row">
                <span class="pdb-label">to call</span>
                <span data-bind="toCall">–</span>
            </div>
            <div class="pdb-row">
                <span class="pdb-label">big blind</span>
                <span data-bind="bigBlind">–</span>
            </div>
            <div class="pdb-row">
                <span class="pdb-label">stack</span>
                <span data-bind="stack">–</span>
            </div>
            <div class="pdb-row">
                <span class="pdb-label">total pot</span>
                <span data-bind="pot">–</span>
            </div>
            <div class="pdb-row">
                <span class="pdb-label">prev phase pot</span>
                <span data-bind="prevPhasePot">–</span>
            </div>
        </div>

        <div class="pdb-section">
            <div class="pdb-label">Hole cards (raw DOM → parsed)</div>
            <div class="pdb-cards" data-bind="hand">–</div>
        </div>

        <div class="pdb-section">
            <div class="pdb-label">Board cards (raw DOM → parsed)</div>
            <div class="pdb-cards" data-bind="board">–</div>
        </div>

        <div class="pdb-section">
            <div class="pdb-label">Actions (real clicks via ui.ts)</div>
            <div class="pdb-buttons">
                <button data-action="fold">fold</button>
                <button data-action="call">call</button>
                <button data-action="check">check</button>
                <button data-action="minRaise">min raise</button>
                <button data-action="halfPotRaise">½ pot raise</button>
                <button data-action="potRaise">pot raise</button>
                <button data-action="allInRaise">all-in raise</button>
            </div>
        </div>

        <button class="pdb-refresh" data-action="refresh">refresh now</button>
    `;

    root.addEventListener("click", (e) => {
        const target = e.target as HTMLElement;
        const action = target.dataset.action;
        if (!action) return;

        switch (action) {
            case "close":
                hideDebugPanel();
                break;
            case "refresh":
                refreshPanel();
                break;
            case "fold":
                fold();
                break;
            case "call":
                call();
                break;
            case "check":
                check();
                break;
            case "minRaise":
                minRaise(() => undefined);
                break;
            case "halfPotRaise":
                halfPotRaise(() => undefined);
                break;
            case "potRaise":
                potRaise(() => undefined);
                break;
            case "allInRaise":
                allInRaise(() => undefined);
                break;
        }
    });

    return root;
}

function bind(name: string): HTMLElement | undefined {
    return panelRoot?.querySelector<HTMLElement>(`[data-bind="${name}"]`);
}

function setText(name: string, value: string, errClass?: string) {
    const el = bind(name);
    if (!el) return;
    el.textContent = value;
    el.classList.remove("pdb-err", "pdb-turn-yes", "pdb-turn-no");
    if (errClass) el.classList.add(errClass);
}

/**
 * Safely calls a reader; on error returns { ok: false, err }.
 * Lets the panel keep refreshing even if a single reader throws.
 */
function safe<T>(fn: () => T): { ok: true; value: T } | { ok: false; err: string } {
    try {
        return { ok: true, value: fn() };
    }
    catch (err) {
        return { ok: false, err: err instanceof Error ? err.message : String(err) };
    }
}

function refreshPanel() {
    if (!panelRoot) return;

    const myTurn = isMyTurn();
    const turnEl = bind("myTurn");
    if (turnEl) {
        turnEl.textContent = myTurn ? "YES" : "no";
        turnEl.classList.remove("pdb-turn-yes", "pdb-turn-no");
        turnEl.classList.add(myTurn ? "pdb-turn-yes" : "pdb-turn-no");
    }

    const phase = safe(getPhase);
    setText("phase",
        phase.ok ? `${phase.value.name} (code ${phase.value.code})` : `ERR: ${phase.err}`,
        phase.ok ? undefined : "pdb-err");

    const handRank = safe(getHandRank);
    setText("handRank",
        handRank.ok ? `${handRank.value.name} (code ${handRank.value.code})` : `ERR: ${handRank.err}`,
        handRank.ok ? undefined : "pdb-err");

    const toCall = safe(getToCallValue);
    setText("toCall",
        toCall.ok ? String(toCall.value) : `ERR: ${toCall.err}`,
        toCall.ok ? undefined : "pdb-err");

    const bigBlind = safe(getBigBlindValue);
    setText("bigBlind",
        bigBlind.ok ? String(bigBlind.value) : `ERR: ${bigBlind.err}`,
        bigBlind.ok ? undefined : "pdb-err");

    const stack = safe(getStack);
    setText("stack",
        stack.ok ? String(stack.value) : `ERR: ${stack.err}`,
        stack.ok ? undefined : "pdb-err");

    const pot = safe(getTotalPot);
    setText("pot",
        pot.ok ? String(pot.value) : `ERR: ${pot.err}`,
        pot.ok ? undefined : "pdb-err");

    const prevPhasePot = safe(getPrevPhasePot);
    setText("prevPhasePot",
        prevPhasePot.ok ? String(prevPhasePot.value) : `ERR: ${prevPhasePot.err}`,
        prevPhasePot.ok ? undefined : "pdb-err");

    renderCards("hand", getHandCards);
    renderCards("board", getBoardCards);

    // disable check button when check isn't legal
    const checkBtn = panelRoot.querySelector<HTMLButtonElement>('button[data-action="check"]');
    if (checkBtn) {
        checkBtn.disabled = !canCheck();
    }
}

/**
 * Renders each card with its raw DOM text (`.value` and `.suit` textContent)
 * next to the parsed value, so a parsing bug is visible at a glance.
 */
function renderCards(bindName: string, getCards: () => Card[]) {
    const container = bind(bindName);
    if (!container) return;

    container.innerHTML = "";
    container.classList.remove("pdb-err");

    let cards: Card[];
    try {
        cards = getCards();
    }
    catch (err) {
        container.textContent = `ERR: ${err instanceof Error ? err.message : String(err)}`;
        container.classList.add("pdb-err");
        return;
    }

    if (cards.length === 0) {
        container.textContent = "–";
        return;
    }

    // Re-find each DOM element by index to grab its raw text alongside the parsed value.
    // Hole cards live under `.you-player .card`; board under `.table-cards .card`.
    const sel = bindName === "hand"
        ? ".you-player .card"
        : ".table-cards .card";
    const els = document.querySelectorAll(sel);

    for (let i = 0; i < cards.length; i++) {
        const card = cards[i];
        const el = els[i];
        const rawValue = el?.querySelector(".value")?.textContent ?? "?";
        const rawSuit = el?.querySelector(".suit")?.textContent ?? "?";

        const div = document.createElement("div");
        div.className = "pdb-card";
        div.innerHTML = `
            <span class="pdb-parsed">${escapeHtml(card.value.name)}${escapeHtml(card.suit)} (code ${card.value.code})</span>
            <span class="pdb-raw">raw: "${escapeHtml(rawValue)}" / "${escapeHtml(rawSuit)}"</span>
        `;
        container.appendChild(div);
    }
}

function escapeHtml(s: string): string {
    return s.replace(/[&<>"']/g, c => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }[c] as string));
}
