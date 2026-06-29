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

    clear() {
        this.length = 0;
        this.logs = [];
    }

    async download(filename: string = `pokerlog_${Date.now()}.json`): Promise<void> {
        const data = JSON.stringify(this.logs, null, 2);
        const blob = new Blob([data], {type: 'application/json'});
        return new Promise((resolve, reject) => {
            chrome.downloads.download({
                url: URL.createObjectURL(blob),
                filename: filename,
                saveAs: true
            }, (downloadId) => {
                if (chrome.runtime.lastError) {
                    reject(chrome.runtime.lastError);
                } else {
                    resolve(downloadId);
                }
            });
        });
    }
}

interface LogEntry {
    timestamp: number;
    action: {type: string; amount?: number | undefined} | null;
    hand: any[]; // Card[]
    board: any[];
    pot?: number;
}