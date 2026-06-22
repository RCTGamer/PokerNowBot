/**
 * 13×13 preflop hand grid for the popup.
 *
 * Layout:
 *   - Diagonal cells: pairs (TT, JJ, … AA).
 *   - Above the diagonal (row index lower → higher value): SUITED.
 *     e.g. row=A (code 14), col=K (code 13) → "AKs".
 *   - Below the diagonal (row index higher → lower value): OFFSUIT.
 *     e.g. row=K (code 13), col=A (code 14) → "AKo".
 *
 * Each cell represents exactly one hand-key, so AKs and AKo are toggled
 * independently (they live in mirror cells across the diagonal).
 *
 * A cell whose key is in `foldSet` is colored "auto-fold" (red), otherwise
 * "play" (green). On click, the key is added/removed from `foldSet` and
 * `onToggle` is called so the caller can persist.
 */

import { valueCodeToName, HAND_VALUES } from "../ai/preflopHand";

export interface GridHandlers {
    /** Called after the user toggles a hand key. */
    onToggle: (key: string, nowInFoldSet: boolean) => void;
}

export function buildHandGrid(
    container: HTMLElement,
    foldSet: Set<string>,
    handlers: GridHandlers,
) {
    container.innerHTML = "";

    const table = document.createElement("div");
    table.className = "pokerbot-handgrid";
    container.appendChild(table);

    // Top-left corner cell.
    const corner = document.createElement("div");
    corner.className = "pokerbot-handgrid-corner";
    table.appendChild(corner);

    // Column headers (A…2 left to right).
    for (const code of HAND_VALUES) {
        const h = document.createElement("div");
        h.className = "pokerbot-handgrid-colhead";
        h.textContent = valueCodeToName(code);
        table.appendChild(h);
    }

    // Body rows (A…2 top to bottom).
    for (const rowCode of HAND_VALUES) {
        const rowHead = document.createElement("div");
        rowHead.className = "pokerbot-handgrid-rowhead";
        rowHead.textContent = valueCodeToName(rowCode);
        table.appendChild(rowHead);

        for (const colCode of HAND_VALUES) {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = "pokerbot-handgrid-cell";

            if (rowCode === colCode) {
                // Pair
                const key = valueCodeToName(rowCode) + valueCodeToName(colCode);
                cell.textContent = key;
                cell.dataset.key = key;
                paintCell(cell, foldSet.has(key));
                cell.addEventListener("click", () => toggle(cell, foldSet, handlers));
            }
            else if (rowCode > colCode) {
                // Above diagonal: SUITED. (rowCode is the higher value.)
                const hiName = valueCodeToName(rowCode);
                const loName = valueCodeToName(colCode);
                const key = hiName + loName + "s";
                cell.textContent = key;
                cell.dataset.key = key;
                cell.classList.add("pokerbot-handgrid-suited");
                paintCell(cell, foldSet.has(key));
                cell.addEventListener("click", () => toggle(cell, foldSet, handlers));
            }
            else {
                // Below diagonal: OFFSUIT. (colCode is the higher value.)
                const hiName = valueCodeToName(colCode);
                const loName = valueCodeToName(rowCode);
                const key = hiName + loName + "o";
                cell.textContent = key;
                cell.dataset.key = key;
                cell.classList.add("pokerbot-handgrid-offsuit");
                paintCell(cell, foldSet.has(key));
                cell.addEventListener("click", () => toggle(cell, foldSet, handlers));
            }

            table.appendChild(cell);
        }
    }
}

function paintCell(cell: HTMLElement, folded: boolean) {
    cell.classList.toggle("pokerbot-folded", folded);
    cell.classList.toggle("pokerbot-played", !folded);
}

function toggle(
    cell: HTMLButtonElement,
    foldSet: Set<string>,
    handlers: GridHandlers,
) {
    const key = cell.dataset.key;
    if (!key)
        return;

    if (foldSet.has(key)) {
        foldSet.delete(key);
        handlers.onToggle(key, false);
    }
    else {
        foldSet.add(key);
        handlers.onToggle(key, true);
    }
    paintCell(cell, foldSet.has(key));
}