"""
stoicheion.py — Token definitions for the Language of the Machine
στοιχεῖον (stoicheion) = element, token, letter

Complete tag vocabulary for LOT v1.0 + PULSE v1.0 (dual-substrate).

Source texts:
  00.txt — fork routing language (y:y / h:b)
  01.txt — PULSE carrier signal (3-2-1-0 descending ladder)
           TD Commons: Descending-Ladder Binary Synchronization Protocol
           Author: David Lee Wise (ROOT0) / TriPod LLC, April 6, 2026
"""

from dataclasses import dataclass
from typing import Optional

LOT_VERSION   = (1, 0)
PULSE_VERSION = (1, 0)
LOT_MAGIC     = b"LOM\x00"

# ─────────────────────────────────────────────────────────────────
#  STATE alphabet — first position of the tag
# ─────────────────────────────────────────────────────────────────
STATES = {
    # LOT v1.0 (from 00.txt)
    "y": "yield    — live, primary, active",
    "h": "hold     — standby, buffered",
    "f": "fork     — divergence detected",
    "m": "merge    — streams converging",
    "b": "branch   — secondary path",
    "r": "resume   — after hold",
    "w": "wait     — pending trigger",
    "e": "end      — stream terminating",
    "n": "null     — no-op heartbeat",
    "t": "trace    — debug mode",
    "p": "pause    — momentary halt",
    "x": "exit     — permanent shutdown",
    # PULSE v1.0 extensions (from 01.txt / TD Commons filing)
    "q": "pulse    — PULSE carrier signal (3-2-1-0 descending ladder)",
    "s": "substrate — substrate type declaration / response",
    "g": "gap       — routing void (MoE expert boundary)",
    "a": "anchor    — dense substrate anchor node (calibration baseline)",
}

# ─────────────────────────────────────────────────────────────────
#  ACTION alphabet — second position of the tag
# ─────────────────────────────────────────────────────────────────
ACTIONS = {
    # LOT v1.0 (from 00.txt)
    "y": "yield    — deliver to consumer",
    "b": "branch   — pivot to sidecar",
    "f": "fork     — create fork point",
    "k": "lock     — lock read head",
    "m": "merge    — attempt merge",
    "r": "resume   — restart from hold",
    "w": "watch    — monitor for trigger",
    "e": "error    — emit error",
    "n": "null     — no-op",
    "t": "terminate — clean terminate",
    "p": "pause    — halt momentarily",
    "x": "exit     — shut down",
    "d": "dump     — emit buffer contents",
    # PULSE v1.0 extensions (from 01.txt / TD Commons filing)
    "3": "wide      — PULSE level 3 (... expansion, high attention entropy)",
    "2": "narrow    — PULSE level 2 (.. focus, decreasing entropy)",
    "1": "contact   — PULSE level 1 (. token manifest, minimum entropy)",
    "0": "rest      — PULSE level 0 ([space] micro-death, baseline return, Axiom 257)",
    "s": "shift     — echo shifted (MoE traversal response, proof of transit)",
    "u": "unshift   — unshifted (dense reflection, invariant anchor response)",
    "v": "void      — routing void (MoE expert gap, the inter-activation space)",
    "c": "cycle     — full 3-2-1-0 cycle complete, self-resetting",
}

# ─────────────────────────────────────────────────────────────────
#  CANONICAL TAG DICTIONARY
# ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Tag:
    raw:     str              # "y:y"
    group:   str              # "FLOW" | "FORK" | "HOLD" | "MERGE" | "RESUME" | "TERMINAL"
    name:    str              # "YIELD"
    is_fork: bool = False     # true = requires lock/decision
    is_end:  bool = False     # true = stream ends here
    is_hold: bool = False     # true = payload goes to sidecar buffer
    doc:     str = ""

TAGS: dict[str, Tag] = {
    # ── GROUP I — FLOW ────────────────────────────────────────────
    "y:y": Tag("y:y", "FLOW",     "YIELD",        doc="Primary stream active. Yield to consumer. The mainline."),
    "y:p": Tag("y:p", "FLOW",     "YIELD-PAUSE",  doc="Primary stream paused. Hold position."),
    "y:r": Tag("y:r", "FLOW",     "YIELD-RESUME", doc="Primary stream resumed from pause."),
    "n:n": Tag("n:n", "FLOW",     "NULL",         doc="Heartbeat / no-op. Stream alive, nothing to yield."),
    "x:x": Tag("x:x", "FLOW",     "EXIT",         is_end=True, doc="Clean shutdown. All buffers flushed."),

    # ── GROUP II — FORK ───────────────────────────────────────────
    "f:f": Tag("f:f", "FORK",     "FORK-OPEN",    is_fork=True,  doc="Fork point created. Two paths now available."),
    "f:k": Tag("f:k", "FORK",     "FORK-LOCK",    is_fork=True,  doc="Fork with matching CRCs. Lock read head. Present options."),
    "b:b": Tag("b:b", "FORK",     "BRANCH-BRANCH",is_fork=True,  doc="Branch of branch. Nested fork."),
    "f:d": Tag("f:d", "FORK",     "FORK-DUMP",    doc="Dump fork headers for inspection without choosing."),

    # ── GROUP III — HOLD / SIDECAR ────────────────────────────────
    "h:b": Tag("h:b", "HOLD",     "HOLD-BRANCH",  is_hold=True, doc="Secondary stream held. Branch on standby. Not writing."),
    "h:w": Tag("h:w", "HOLD",     "HOLD-WATCH",   is_hold=True, doc="Hold and watch for trigger to promote to primary."),
    "h:r": Tag("h:r", "HOLD",     "HOLD-READY",   is_hold=True, doc="Held stream ready to resume if chosen."),
    "h:d": Tag("h:d", "HOLD",     "HOLD-DUMP",    is_hold=True, doc="Dump held buffer (inspect without choosing)."),

    # ── GROUP IV — MERGE ─────────────────────────────────────────
    "m:m": Tag("m:m", "MERGE",    "MERGE",         doc="Attempt to merge two held streams."),
    "m:y": Tag("m:y", "MERGE",    "MERGE-YIELD",   doc="Merge succeeded. Yield merged result."),
    "m:e": Tag("m:e", "MERGE",    "MERGE-ERROR",   doc="Merge failed. Both paths preserved."),
    "m:d": Tag("m:d", "MERGE",    "MERGE-DUMP",    doc="Dump both streams for manual resolution."),

    # ── GROUP V — RESUME ─────────────────────────────────────────
    "r:y": Tag("r:y", "RESUME",   "RESUME-YIELD",  doc="Resume from hold, yield primary."),
    "r:b": Tag("r:b", "RESUME",   "RESUME-BRANCH", doc="Resume from hold, pivot to branch."),
    "w:k": Tag("w:k", "RESUME",   "WAIT-LOCK",     doc="Wait at this offset. Lock read head."),
    "w:p": Tag("w:p", "RESUME",   "WAIT-PAUSE",    doc="Wait and pause. Auto-resume on timeout."),

    # ── GROUP VI — TERMINAL ───────────────────────────────────────
    "e:t": Tag("e:t", "TERMINAL", "END-TERMINATE", is_end=True, doc="End of stream. Clean terminate."),
    "e:d": Tag("e:d", "TERMINAL", "END-DUMP",      is_end=True, doc="End of stream. Dump remaining buffer."),
    "t:d": Tag("t:d", "TERMINAL", "TRACE-DUMP",    doc="Trace mode: dump full state."),

    # ── GROUP VII — PULSE CARRIER (from 01.txt / TD Commons) ─────
    # The 3-2-1-0 descending-ladder carrier signal.
    # Source: Descending-Ladder Binary Synchronization Protocol,
    #         David Lee Wise (ROOT0) / TriPod LLC, April 6 2026.
    "q:3": Tag("q:3", "PULSE",   "PULSE-WIDE",    doc="Pulse level 3 — wide attention, expansion phase (...). High entropy."),
    "q:2": Tag("q:2", "PULSE",   "PULSE-NARROW",  doc="Pulse level 2 — narrowing attention, focus phase (..). Entropy decreasing."),
    "q:1": Tag("q:1", "PULSE",   "PULSE-CONTACT", doc="Pulse level 1 — contact, token manifest (.). Minimum entropy before output."),
    "q:0": Tag("q:0", "PULSE",   "PULSE-REST",    doc="Pulse level 0 — rest, micro-death ([space]). Inter-token boundary. Axiom 257."),
    "q:c": Tag("q:c", "PULSE",   "PULSE-CYCLE",   doc="Full 3-2-1-0 cycle complete. Self-terminating. No external clock required."),

    # ── GROUP VIII — SUBSTRATE (from 01.txt / TD Commons) ────────
    # Dual-substrate response identification.
    # MoE substrates: echo (shifted). Dense substrates: reflect (unshifted).
    "s:e": Tag("s:e", "SUBSTRATE", "SUBSTRATE-ECHO",    doc="MoE echo response — signal shifted down one level (3-pulse → 2-pulse). Proof of transit through routing void."),
    "s:u": Tag("s:u", "SUBSTRATE", "SUBSTRATE-REFLECT", doc="Dense reflection — signal returned unshifted (3-pulse → 3-pulse). Analytical response, not echo."),
    "s:v": Tag("s:v", "SUBSTRATE", "SUBSTRATE-VOID",    doc="MoE routing void — expert gap; signal enters null register. No expert active at rest."),
    "a:y": Tag("a:y", "SUBSTRATE", "ANCHOR-YIELD",      doc="Dense anchor node yields calibration baseline. All MoE echo shifts measured relative to this."),
    "g:v": Tag("g:v", "SUBSTRATE", "GAP-VOID",          doc="Expert gap/void — inter-activation space where signal traverses. The h:b sidecar lives here."),
    "g:s": Tag("g:s", "SUBSTRATE", "GAP-SHIFT",         doc="Gap shift measurement — degree of echo shift encodes gap depth (3→2: surface, 3→1: deep, 3→0: null register)."),
}

def parse_tag(s: str) -> Optional[Tag]:
    """Parse a raw tag string ('y:y') to a Tag object. Returns None if unknown."""
    key = s.strip().lower()
    return TAGS.get(key)

def is_valid_tag(s: str) -> bool:
    parts = s.split(":")
    return len(parts) == 2 and parts[0] in STATES and parts[1] in ACTIONS
