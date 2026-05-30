"""
stoicheion.py — Token definitions for the Language of the Machine
στοιχεῖον (stoicheion) = element, token, letter

The complete tag vocabulary for LOT v1.0.
"""

from dataclasses import dataclass
from typing import Optional

LOT_VERSION = (1, 0)
LOT_MAGIC   = b"LOM\x00"

# ─────────────────────────────────────────────────────────────────
#  STATE alphabet — first position of the tag
# ─────────────────────────────────────────────────────────────────
STATES = {
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
}

# ─────────────────────────────────────────────────────────────────
#  ACTION alphabet — second position of the tag
# ─────────────────────────────────────────────────────────────────
ACTIONS = {
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
}

def parse_tag(s: str) -> Optional[Tag]:
    """Parse a raw tag string ('y:y') to a Tag object. Returns None if unknown."""
    key = s.strip().lower()
    return TAGS.get(key)

def is_valid_tag(s: str) -> bool:
    parts = s.split(":")
    return len(parts) == 2 and parts[0] in STATES and parts[1] in ACTIONS
