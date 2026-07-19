/**
 * Background service worker — owns the chrome.downloads call.
 *
 * Why: the content script (main.ts) runs in the page's isolated world, where
 * Manifest V3 forbids chrome.downloads. The popup can use it, but the popup
 * closes when the user clicks elsewhere, so we cannot reliably persist heavy
 * data through it. The service worker is the only context that (a) has
 * chrome.downloads and (b) survives past the popup.
 *
 * Why a data: URL (and not a blob: URL):
 *   Chrome MV3 extension service workers intentionally disable
 *   URL.createObjectURL (see Chrome docs: "Limitations of service workers"
 *   under Network requests). A `data:application/json,...` URL works in any
 *   Chrome context — service worker, popup, content script.
 *
 * Protocol:
 *   content-script sends { type: "download_logs", data, filename }
 *   → we wrap `data` as a data URL, hand it to chrome.downloads, then reply
 *     with { ok, downloadId } or { error }.
 */

/** Internal message contract between the content script and this worker. */
type DownloadLogsRequest = {
    type: "download_logs";
    /** Pre-serialized JSON string from the content script's logger. */
    data: string;
    /** File name to save as. */
    filename: string;
};

type DownloadLogsResponse =
    | { ok: true; downloadId: number }
    | { error: string };

chrome.runtime.onMessage.addListener(
    (message: DownloadLogsRequest, _sender, sendResponse: (r: DownloadLogsResponse) => void) => {
        if (!message || message.type !== "download_logs") {
            return false;
        }

        try {
            // data: URLs work everywhere blob: URLs do in MV3, and unlike
            // blob: URLs they're not blocked inside extension service workers.
            const dataUrl =
                "data:application/json;charset=utf-8," +
                encodeURIComponent(message.data);

            chrome.downloads.download(
                {
                    url: dataUrl,
                    filename: message.filename,
                    saveAs: true,
                },
                (downloadId) => {
                    if (chrome.runtime.lastError) {
                        sendResponse({ error: chrome.runtime.lastError.message });
                    }
                    else {
                        sendResponse({ ok: true, downloadId });
                    }
                },
            );

            // Returning true keeps the message channel open for the async
            // sendResponse call above.
            return true;
        }
        catch (err) {
            sendResponse({ error: err instanceof Error ? err.message : String(err) });
            return false;
        }
    },
);

