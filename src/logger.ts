export class Logger {
    private logs: LogEntry[] = [];

    log(action: Action | undefined, state: State) {
        const entry: LogEntry = {
            timestamp: Date.now(),
            action: action ? { type: action.type, amount: (action as any).amount ?? undefined } : null,
            // Assuming Card objects have suit and value properties; we keep them as-is for simplicity
            hand: state.hand.slice(), // shallow copy
            board: state.board.slice(),
            pot: state.pot ?? undefined,
        };
        this.logs.push(entry);
    }

    getLogs(): LogEntry[] {
        return [...this.logs];
    }

    /**
     * Reset the in-memory log buffer. (Bug fix: prior version set
     * `this.length = 0`, which silently did nothing — `logs` is the
     * actual field.)
     */
    clear() {
        this.logs.length = 0;
    }

    // NOTE: previous version of this class had a `download(filename)`
    // method that did logging + chrome.downloads.download locally.
    // Removed because in MV3 `chrome.downloads` is undefined inside
    // content scripts (it lives in the service worker only). The
    // download pipeline now goes:
    //   popup → main.ts → chrome.runtime.sendMessage →
    //   background.ts (data: URL) → chrome.downloads.download.
}

interface LogEntry {
    timestamp: number;
    action: {type: string; amount?: number | undefined} | null;
    hand: any[]; // Card[]
    board: any[];
    pot?: number;
}