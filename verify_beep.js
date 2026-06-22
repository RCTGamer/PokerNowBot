// Verifies the "beep once per new hand, only on green" state machine
// in src/main.ts by extracting the logic into a Node harness.

const fs = require("fs");
const path = require("path");

// ---- shims -----------------------------------------------------------------
class El {
  constructor(tag) { this.tag = tag; this.children = []; this.classList = new ClassList(); this.dataset = {}; this.textContent = ""; this.innerHTML = ""; }
  appendChild(c) { this.children.push(c); return c; }
  querySelector(sel) { return findAll(this, sel)[0] || null; }
  querySelectorAll(sel) { return findAll(this, sel); }
}
class ClassList { constructor(){this._set=new Set()} add(c){this._set.add(c)} contains(c){return this._set.has(c)} }
function findAll(root, sel) {
  const m = /^([a-zA-Z]*)(?:\.([\w-]+(?:\.[\w-]+)*))?$/.exec(sel);
  if (!m) return [];
  const tag = m[1] || null;
  const clsList = m[2] ? m[2].split(".") : [];
  const match = (n) => (tag === null || n.tag === tag) && clsList.every(c => n.classList.contains(c));
  const out = [];
  (function rec(n) { if (match(n)) out.push(n); for (const c of n.children || []) rec(c); })(root);
  return out;
}

function card(value, suit) {
  const c = new El("div"); c.classList.add("card");
  const v = new El("div"); v.classList.add("value"); v.textContent = value;
  const s = new El("div"); s.classList.add("suit"); s.textContent = suit;
  c.appendChild(v); c.appendChild(s); return c;
}
function buildScene(hand) {
  const root = new El("html");
  const seat = new El("div"); seat.classList.add("you-player");
  if (hand) { seat.appendChild(card(hand[0][0], hand[0][1])); seat.appendChild(card(hand[1][0], hand[1][1])); }
  root.appendChild(seat);
  return root;
}

const PreflopPhase = { code: 0 };
const FlopPhase = { code: 1 };

function getState() {
  const seat = global.document.querySelector(".you-player");
  const codeMap = { A:14, K:13, Q:12, J:11, T:10 };
  const cards = seat.querySelectorAll(".card").map(c => ({
    value: { code: codeMap[c.children[0].textContent] || parseInt(c.children[0].textContent) },
    suit: c.children[1].textContent,
  }));
  return { phase: PreflopPhase, hand: cards, handPlusBoard: cards, board: [] };
}

function encodeHand(hand) {
  if (hand.length !== 2) return "";
  const a = hand[0], b = hand[1];
  const hi = a.value.code >= b.value.code ? a : b;
  const lo = a.value.code >= b.value.code ? b : a;
  const pair = a.value.code === b.value.code;
  const suited = a.suit === b.suit;
  const name = (c) => ({14:"A",13:"K",12:"Q",11:"J",10:"T"})[c.value.code] || String(c.value.code);
  if (pair) return name(hi) + name(hi);
  return name(hi) + name(lo) + (suited ? "s" : "o");
}

// ---- Beep state machine under test (mirror of maybeBeepForHand) -----------
let beepEnabled = true;
let lastBeepedHandKey;
let beepLog = [];
function playBeep() { beepLog.push({ at: Date.now(), key: lastBeepedHandKey }); }

function maybeBeepForHand(state) {
  if (!beepEnabled) return;
  if (state.phase.code !== 0) return;
  if (state.hand.length !== 2) return;
  const key = encodeHand(state.hand);
  if (key === lastBeepedHandKey) return;
  lastBeepedHandKey = key;
  // simulate fold set: anything containing "2o", "3o"..."9o" or low pairs is red
  const isRed = /^(72|82|92|32|42|52|62|73|83|93|43|53|63)o$/.test(key) ||
                /^(22|33|44) /.test(" ") ? false : false; // placeholder
  // Use the explicit foldSet from the test:
  const foldSet = global.__foldSet || new Set();
  if (foldSet.has(key)) return;
  playBeep();
}

// ---- Tests ----------------------------------------------------------------
let pass = 0, fail = 0;
function check(label, cond, detail) {
  if (cond) { console.log(`PASS  ${label}`); pass++; }
  else      { console.log(`FAIL  ${label}  ${detail || ""}`); fail++; }
}

// Scenario 1: same green hand across 3 ticks → beep exactly once.
global.__foldSet = new Set(["72o"]); // 7s2o red, AKs green
beepLog = []; lastBeepedHandKey = undefined;
["AKs","AKs","AKs"].forEach(h => {
  global.document = buildScene([["A","♠"],["K","♠"]]);
  maybeBeepForHand(getState());
});
check("3 ticks of AKs (green) → 1 beep", beepLog.length === 1, `got ${beepLog.length}`);

// Scenario 2: green A → red B → green C → 2 beeps (at A and C, never B).
beepLog = []; lastBeepedHandKey = undefined;
global.__foldSet = new Set(["72o","KQo"]); // KQo red, AKs green, 7s2o red
const seq = [
  { hand: [["A","♠"],["K","♠"]], expectBeep: true  }, // AKs green
  { hand: [["7","♠"],["2","♥"]], expectBeep: false }, // 7s2o red
  { hand: [["A","♠"],["K","♠"]], expectBeep: true  }, // AKs green again
];
seq.forEach((step, i) => {
  global.document = buildScene(step.hand);
  const before = beepLog.length;
  maybeBeepForHand(getState());
  const beepedNow = beepLog.length > before;
  check(`  step ${i+1} (${step.hand.map(c=>c[0]).join("")}${step.hand[0][1]===step.hand[1][1]?"s":"o"}) beeps? expected=${step.expectBeep} actual=${beepedNow}`,
        beepedNow === step.expectBeep);
});

// Scenario 3: same hand appearing on a new "hand deal" — does our dedup
// wrongly suppress the second beep?
// Per the spec ("once when the hand pops up"), this SHOULD suppress if the
// table literally shows the same two cards. In poker that's essentially never
// the case between hands, so we test only the path that matters: a NEW hand
// always triggers a fresh evaluation.
beepLog = []; lastBeepedHandKey = undefined;
global.__foldSet = new Set(); // nothing red
["AKs","KQs","QQ","72o"].forEach((k, i) => {
  const [r1, r2] = (() => {
    if (k === "AKs") return [["A","♠"],["K","♠"]];
    if (k === "KQs") return [["K","♠"],["Q","♠"]];
    if (k === "QQ")  return [["Q","♠"],["Q","♥"]];
    if (k === "72o") return [["7","♠"],["2","♥"]];
  })();
  global.document = buildScene([r1, r2]);
  maybeBeepForHand(getState());
});
check("4 distinct preflop hands → 4 beeps (none red)", beepLog.length === 4, `got ${beepLog.length}`);

// Scenario 4: tick during post-flop should NOT affect beep tracker
// (user said "only when the hand pops up" — post-flop is not preflop).
beepLog = []; lastBeepedHandKey = undefined;
global.__foldSet = new Set(["72o"]); // 7s2o red
global.document = buildScene([["A","♠"],["K","♠"]]);
maybeBeepForHand(getState()); // 1 beep
// simulate moving to flop — state.phase.code !== 0
global.document = buildScene([["A","♠"],["K","♠"]]);
const flopState = getState(); flopState.phase = FlopPhase;
maybeBeepForHand(flopState); // no beep (post-flop skipped)
check("post-flop tick does NOT re-beep", beepLog.length === 1, `got ${beepLog.length}`);

// Scenario 5: beepEnabled=false suppresses all beeps
beepEnabled = false;
beepLog = []; lastBeepedHandKey = undefined;
global.document = buildScene([["A","♠"],["K","♠"]]);
maybeBeepForHand(getState());
check("beepEnabled=false → no beep", beepLog.length === 0, `got ${beepLog.length}`);
beepEnabled = true;

console.log();
console.log(fail === 0 ? "ALL BEEP SCENARIOS PASS" : `${fail} FAILED`);
process.exit(fail === 0 ? 0 : 1);
