/**
 * Single-tone beep via WebAudio. Lazy-initializes the AudioContext on first
 * call so we don't fight autoplay policies before the user has interacted.
 *
 * Browser autoplay policies require that AudioContext be created or resumed
 * inside a user-gesture handler. In practice the bot's user has already
 * clicked "start bot" or "debug" before this is called, which Chrome treats
 * as a gesture context lasting the lifetime of the tab.
 */

const BEEP_FREQUENCY_HZ = 880;
const BEEP_DURATION_S = 0.7;
// "Softer" beep: roughly 40% of the original 0.2 peak gain.
// Still audible as a tap, but won't startle on every playable hand.
const BEEP_GAIN_PEAK = 0.08;
const RAMP_S = 0.01;

let audioContext: AudioContext | undefined;

function getAudioContext(): AudioContext {
    if (audioContext)
        return audioContext;

    // Use the standard constructor, with a fallback for older WebKit.
    const Ctor = window.AudioContext ?? (window as any).webkitAudioContext;
    audioContext = new Ctor();
    return audioContext;
}

/**
 * Play a short attention beep. Safe to call repeatedly — overlapping calls
 * simply play multiple oscillators at once.
 */
export function playBeep(): void {
    let ctx: AudioContext;
    try {
        ctx = getAudioContext();
    }
    catch (err) {
        // AudioContext not supported (very old browser, or strict iframe).
        // The bot still works, it just won't beep.
        console.warn("beep: AudioContext unavailable", err);
        return;
    }

    // Some browsers leave the context in "suspended" state until a gesture
    // has occurred; resume() is idempotent and safe.
    if (ctx.state === "suspended")
        ctx.resume().catch(() => undefined);

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "square";
    osc.frequency.setValueAtTime(BEEP_FREQUENCY_HZ, now);

    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(BEEP_GAIN_PEAK, now + RAMP_S);
    gain.gain.setValueAtTime(BEEP_GAIN_PEAK, now + BEEP_DURATION_S - RAMP_S);
    gain.gain.linearRampToValueAtTime(0, now + BEEP_DURATION_S);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + BEEP_DURATION_S + 0.05);
}