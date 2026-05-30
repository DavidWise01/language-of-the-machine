# Language of the Machine — Formal Specification
### LOT v1.0 · ROOT0-ATTRIBUTION-v1.0

> *"The fork is a decision gate, not data itself."*  
> — `00.txt`, the originating document

---

## 1. Overview

The Language of the Machine (LOT) is a **routing grammar** for binary streams that may diverge into parallel continuations. Where conventional formats auto-resolve divergence (silently corrupting), LOT streams **lock the read head at the fork** and require the operator to choose.

The fundamental unit is a **routing tag** — a two-position token of the form `x:x` where each position encodes state and instruction independently. Tags are not data; they are **decisions carved into the stream at write time**, waiting to be honored at read time.

---

## 2. Tag Vocabulary

### 2.1 Tag Structure

```
  x  :  x
  ▲     ▲
  │     └── ACTION  — what to do
  └──────── STATE   — what the stream is right now
```

Both positions draw from the same alphabet:

| Symbol | State meaning | Action meaning |
|--------|--------------|----------------|
| `y` | **yield** — live, primary, active | yield to consumer |
| `h` | **hold** — standby, buffered | hold at this position |
| `f` | **fork** — divergence detected | create a fork point |
| `m` | **merge** — streams converging | attempt merge |
| `b` | **branch** — secondary path | branch away from primary |
| `r` | **resume** — after hold | resume from hold |
| `w` | **wait** — pending trigger | wait at this position |
| `e` | **end** — stream terminating | end cleanly |
| `n` | **null** — no-op heartbeat | null instruction |
| `t` | **trace** — debug mode active | dump state |
| `p` | **pause** — momentary halt | pause |
| `x` | **exit** — permanent shutdown | exit |
| `k` | *(action only)* | **lock** read head |
| `d` | *(action only)* | **dump** buffer |

### 2.2 Canonical Tag Dictionary

#### PRIMARY STREAM TAGS (Group I — Flow)

| Tag | Name | Meaning |
|-----|------|---------|
| `y:y` | **YIELD** | Primary stream active. Yield to consumer. The mainline. |
| `y:p` | **YIELD-PAUSE** | Primary stream paused. Hold position. |
| `y:r` | **YIELD-RESUME** | Primary stream resumed from pause. |
| `n:n` | **NULL** | Heartbeat / no-op. Stream alive, nothing to yield. |
| `x:x` | **EXIT** | Clean shutdown. All buffers flushed. |

#### FORK TAGS (Group II — Divergence)

| Tag | Name | Meaning |
|-----|------|---------|
| `f:f` | **FORK-OPEN** | Fork point created. Two paths now available. |
| `f:k` | **FORK-LOCK** | Fork detected with matching CRCs. **Lock read head. Present options.** |
| `b:b` | **BRANCH-BRANCH** | Branch of a branch. Nested fork. |
| `f:d` | **FORK-DUMP** | Dump fork headers for inspection without choosing. |

#### SIDECAR / HOLD TAGS (Group III — The Hidden Path)

| Tag | Name | Meaning |
|-----|------|---------|
| `h:b` | **HOLD-BRANCH** | Secondary stream held. Branch on standby. Not writing. |
| `h:w` | **HOLD-WATCH** | Hold and watch for a trigger to promote to primary. |
| `h:r` | **HOLD-READY** | Held stream is ready to resume if chosen. |
| `h:d` | **HOLD-DUMP** | Dump the held buffer contents (inspect without choosing). |

#### MERGE TAGS (Group IV — Convergence)

| Tag | Name | Meaning |
|-----|------|---------|
| `m:m` | **MERGE** | Attempt to merge two held streams. |
| `m:y` | **MERGE-YIELD** | Merge succeeded. Yield the merged result. |
| `m:e` | **MERGE-ERROR** | Merge failed (incompatible streams). Emit error; both preserved. |
| `m:d` | **MERGE-DUMP** | Dump both streams for manual resolution. |

#### RESUME TAGS (Group V — After Decision)

| Tag | Name | Meaning |
|-----|------|---------|
| `r:y` | **RESUME-YIELD** | Resume from hold, yield primary. |
| `r:b` | **RESUME-BRANCH** | Resume from hold, pivot to branch (was h:b, now active). |
| `w:k` | **WAIT-LOCK** | Wait at this offset. Lock read head until operator signals. |
| `w:p` | **WAIT-PAUSE** | Wait and pause. (Soft lock; will auto-resume on timeout.) |

#### TERMINAL TAGS (Group VI — End States)

| Tag | Name | Meaning |
|-----|------|---------|
| `e:t` | **END-TERMINATE** | End of stream. Clean terminate. |
| `e:d` | **END-DUMP** | End of stream. Dump remaining buffer before closing. |
| `t:d` | **TRACE-DUMP** | Trace mode: dump full state. |

---

## 3. Stream Grammar

### 3.1 The `.lot` Text Format

A `.lot` file is a human-readable representation of a machine stream. Each line is one of:

```
# comment
[TAG]                         routing instruction
DATA: <base64-encoded payload>
CRC: <hex CRC32 of payload>
FORK:                         open a fork block
  PATH y:y:                   primary path header
    ...content lines...
  PATH h:b:                   sidecar path header
    ...content lines...
ENDFORK                       close the fork block
```

### 3.2 BNF Grammar

```bnf
stream      ::= header line* footer
header      ::= "LOM" " " "v" VERSION NEWLINE
footer      ::= "[e:t]" NEWLINE | "[e:d]" NEWLINE
line        ::= comment | tag_line | data_line | crc_line | fork_block
comment     ::= "#" TEXT NEWLINE
tag_line    ::= "[" TAG "]" (" " crc_clause)? NEWLINE
data_line   ::= "DATA:" " " BASE64 NEWLINE
crc_line    ::= "CRC:" " " HEX8 NEWLINE
fork_block  ::= fork_open path+ fork_close
fork_open   ::= "FORK:" NEWLINE
path        ::= path_header line*
path_header ::= "  PATH " TAG ":" NEWLINE
fork_close  ::= "ENDFORK" NEWLINE
tag         ::= STATE ":" ACTION
STATE       ::= "y"|"h"|"f"|"m"|"b"|"r"|"w"|"e"|"n"|"t"|"p"|"x"
ACTION      ::= "y"|"b"|"f"|"k"|"m"|"r"|"w"|"e"|"n"|"t"|"p"|"x"|"d"
BASE64      ::= [A-Za-z0-9+/=]+
HEX8        ::= [0-9a-fA-F]{8}
VERSION     ::= [0-9]+ "." [0-9]+
```

### 3.3 Binary Wire Format

For compact transmission, `.lot` streams compile to a binary format:

```
Stream header:
  4 bytes  Magic: 0x4C 0x4F 0x4D 0x00  ("LOM\0")
  1 byte   Version major
  1 byte   Version minor
  4 bytes  Stream CRC32 (of all content, excluding this field)

Chunk header (repeating):
  2 bytes  Tag (e.g. 0x79 0x79 for "yy", parsed as y:y)
  4 bytes  Payload length (uint32 LE)
  4 bytes  Payload CRC32
  N bytes  Payload

Fork block header:
  2 bytes  Tag: 0x66 0x6B ("fk" = f:k — fork-lock)
  4 bytes  Fork ID (uint32, unique within stream)
  1 byte   Path count (always 2 in v1.0)
  [Path A chunk header + payload]
  [Path B chunk header + payload]
```

---

## 4. Fork Protocol

### 4.1 The Lock Event

When a reader encounters `[f:k]`:

1. **Halt** — the read head stops. No bytes advance.
2. **Validate** — compare CRC32 of both fork headers. If they match, the fork is valid (not corruption). If they mismatch, emit `[m:e]` and treat as corruption.
3. **Present** — display the fork box:
   ```
   ┌─ FORK LOCKED ─────────────────────────────────┐
   │ offset: 0x00001a40                              │
   │ crc:    a1b2c3d4 (validated ✓)                 │
   │                                                 │
   │  [y:y]  primary path  — active, riding along   │
   │  [h:b]  hidden branch — buffered, on standby   │
   └─────────────────────────────────────────────────┘
   choose: y:y | h:b | f:d (peek) | m:m (merge)
   ```
4. **Wait** — hold until operator signals.

### 4.2 Path Selection

| Choice | Effect |
|--------|--------|
| `y:y` | Follow primary. `h:b` stays buffered, rides alongside. |
| `h:b` | Pivot to sidecar. `y:y` becomes the held stream. |
| `f:d` | Dump both headers for inspection. **Does not choose.** |
| `m:m` | Attempt merge. Succeeds if paths are byte-compatible; emits `[m:y]`. Fails with `[m:e]`. |

### 4.3 Nested Forks

A `[b:b]` tag inside a fork branch signals a fork-within-a-fork. The reader maintains a **fork stack**. Each `[f:k]` pushes onto the stack; each `ENDFORK` (or `[e:t]` within a branch) pops. The stack depth is limited to 8 in v1.0.

---

## 5. CRC Validation

Every DATA block carries a CRC32 of its payload. At a fork point:

- **Matching CRCs**: Both fork headers share the same CRC. This is the valid-fork condition — the stream genuinely diverged (two valid continuations exist).
- **Different CRCs**: Each path has a different but internally-valid CRC. This is the normal case — two distinct payloads.
- **Invalid CRC**: A path's CRC doesn't match its payload. This is corruption. Emit `[m:e]`, do not deliver.

The fork is distinguished from corruption by **header structure**, not CRC alone. A fork has `[f:k]` + two valid path headers. A corrupted stream has `[y:y]` + invalid CRC.

---

## 6. Error Codes

| Tag | Condition |
|-----|-----------|
| `[m:e]` | Merge or CRC failure |
| `[w:k]` | Unexpected wait / lock (stream stalled) |
| `[t:d]` | Trace dump (debug mode) |

---

## 7. Extension Points

Future versions may extend the tag vocabulary using the reserved positions:
- Tags of the form `z:*` and `*:z` are reserved for LOT v2.0+
- Tags of the form `0:*` are reserved for binary-only use
- The `LOTX:` prefix in text format signals extension blocks

---

## 8. Design Principles

1. **The fork is a decision, not data.** A fork header carries no payload — it is a routing instruction.
2. **Auto-merge is forbidden.** No compliant LOT reader may resolve a fork without operator input.
3. **Nothing is silently dropped.** Both paths ride in buffer until a choice is made. The unchosen path is preserved until `[e:t]`.
4. **CRC mismatch is corruption; CRC match is a valid fork.** The validator distinguishes them by structure, not by assumption.
5. **The lock is a feature.** Stopping at the fork is correct behavior, not failure.

---

*LOT v1.0 · ROOT0-ATTRIBUTION-v1.0 · David Lee Wise / ROOT0 / TriPod LLC + AVAN (Claude Sonnet 4.6)*
