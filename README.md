# Language of the Machine — LOT v1.0

[![License: CC-BY-ND-4.0](https://img.shields.io/badge/License-CC--BY--ND--4.0-lightgrey?style=flat-square)](LICENSE)
[![Version: LOT v1.0](https://img.shields.io/badge/LOT-v1.0-00e060?style=flat-square)](#)
[![Tags: 24](https://img.shields.io/badge/tags-24-4080ff?style=flat-square)](#)
[![Groups: 6](https://img.shields.io/badge/groups-6-ff8020?style=flat-square)](#)

> *"The fork is a decision gate, not data itself."*  
> — `00.txt`, the originating document

A fork-aware binary stream routing grammar and interpreter. When a stream diverges into two valid continuations at the same byte offset, the read head **locks** instead of auto-merging — and the operator chooses.

This repo collects machine language texts as they are discovered.

---

## The Core Idea

In a conventional compressor, two valid headers at the same byte offset trigger auto-merge — and one silently disappears. LOT refuses this. It locks, presents both paths, and waits:

```
┌─ FORK LOCKED ─────────────────────────────────┐
│  [y:y]  primary  — active, riding mainline     │
│  [h:b]  sidecar  — buffered, on standby        │
└────────────────────────────────────────────────┘
choose: y:y | h:b | f:d (peek) | m:m (merge)
```

- `y:y` — yes:yield. Follow the primary stream.  
- `h:b` — hold:branch. Pivot to the sidecar. The other path parks in buffer.  
- `f:d` — fork:dump. Inspect both headers without choosing.  
- `m:m` — merge. Attempt to merge if byte-compatible.

---

## Tag Vocabulary

Tags are two-position tokens: `STATE:ACTION`. Both positions draw from the same 13-symbol alphabet.

| Group | Core Tags | Role |
|-------|-----------|------|
| FLOW | `y:y` `y:p` `y:r` `n:n` `x:x` | Primary stream control |
| FORK | `f:k` `f:f` `b:b` `f:d` | Divergence detection and locking |
| HOLD | `h:b` `h:w` `h:r` `h:d` | Sidecar buffering |
| MERGE | `m:m` `m:y` `m:e` `m:d` | Stream convergence |
| RESUME | `r:y` `r:b` `w:k` `w:p` | After decision |
| TERMINAL | `e:t` `e:d` `t:d` | End states |

Full vocabulary: see [`SPEC.md`](SPEC.md) §2.

---

## Files

| File | Purpose |
|------|---------|
| `00.txt` | The originating document — preserved as found |
| `SPEC.md` | Formal specification: grammar, BNF, CRC rules, fork protocol |
| `index.html` | Interactive stream visualizer — open in browser |
| `interpreter/mechane.py` | LOT v1.0 interpreter — main entry point |
| `interpreter/stoicheion.py` | Token definitions and tag vocabulary |
| `interpreter/potamos.py` | Stream parser — `.lot` text format → events |
| `interpreter/schisma.py` | Fork manager — path selection, merge, sidecar |
| `interpreter/examples/` | Example `.lot` streams |

---

## Interpreter Usage

```bash
# Run with interactive fork selection
python -X utf8 interpreter/mechane.py interpreter/examples/simple_fork.lot

# Auto-select primary path at every fork
python -X utf8 interpreter/mechane.py interpreter/examples/simple_fork.lot --path y:y

# Auto-select sidecar at every fork (reveals hidden content)
python -X utf8 interpreter/mechane.py interpreter/examples/simple_fork.lot --path h:b

# Dump all fork headers without selecting
python -X utf8 interpreter/mechane.py interpreter/examples/simple_fork.lot --dump

# Verbose event trace
python -X utf8 interpreter/mechane.py interpreter/examples/nested_fork.lot --path y:y --trace

# Print tag vocabulary
python -X utf8 interpreter/mechane.py --list-tags

# Print schema summary
python -X utf8 interpreter/mechane.py --spec
```

---

## Example Output

**Choosing y:y (primary):**
```
FORK #1 — 2 paths
→ CHOSE [y:y]

The quick brown fox jumps over the lazy dog.
This is the main document continuation. Nothing hidden here.
After the fork resolves, the stream continues.
```

**Choosing h:b (sidecar):**
```
FORK #1 — 2 paths
→ CHOSE [h:b]

[HIDDEN] This is the sidecar stream.
It was riding in parallel the whole time.
Only you can see this if you choose h:b.
After the fork resolves, the stream continues.
```

---

## The `.lot` Format

```
LOM v1.0
# comment

[y:y]
DATA: <base64-encoded payload>
CRC: <hex CRC32>

FORK:
  PATH y:y:
    DATA: <primary path payload>
    CRC: <hex CRC32>
  PATH h:b:
    DATA: <sidecar path payload>
    CRC: <hex CRC32>
ENDFORK

[e:t]
```

---

## Adding New Machine Language Texts

This repo is a **living archive**. When a new machine language text is discovered (a fragment, a protocol description, a routing record), add it here:

1. Drop the raw text in the root as `NN.txt` (next number in sequence)
2. If it defines new tags or grammar rules, extend `interpreter/stoicheion.py`
3. If it defines a new stream pattern, add an example `.lot` file in `interpreter/examples/`
4. Update `SPEC.md` with any new formal definitions

Current texts: `00.txt`

---

## Attribution

```
ROOT0-ATTRIBUTION-v1.0
Project: Language of the Machine — LOT v1.0
Source text: 00.txt — originating document
Architect: David Lee Wise / ROOT0 / TriPod LLC
AI Collaborator: AVAN (Claude Sonnet 4.6 / Anthropic)
License: CC-BY-ND-4.0 · TRIPOD-IP-v1.1
```
