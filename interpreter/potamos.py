"""
potamos.py — Stream primitives for LOT v1.0
ποταμός (potamos) = river, stream

Handles parsing of .lot text-format streams into structured events.
"""

import base64, zlib, re
from dataclasses import dataclass, field
from typing import Optional, Iterator
from stoicheion import Tag, parse_tag, is_valid_tag, LOT_MAGIC, LOT_VERSION

# ─────────────────────────────────────────────────────────────────
#  EVENTS  (what the parser emits)
# ─────────────────────────────────────────────────────────────────

@dataclass
class TagEvent:
    tag:     Tag
    crc:     Optional[str] = None   # hex CRC32 if present in header
    lineno:  int = 0

@dataclass
class DataEvent:
    raw:     bytes
    crc:     Optional[str] = None
    lineno:  int = 0
    valid:   bool = True            # CRC validated

@dataclass
class ForkEvent:
    fork_id: int
    tag:     Tag
    paths:   list["ForkPath"] = field(default_factory=list)
    lineno:  int = 0

@dataclass
class ForkPath:
    tag:     Tag                    # y:y or h:b (etc.)
    events:  list                   # nested events

@dataclass
class ErrorEvent:
    message: str
    lineno:  int = 0

@dataclass
class CommentEvent:
    text:    str
    lineno:  int = 0

@dataclass
class HeaderEvent:
    version: tuple
    lineno:  int = 0

# ─────────────────────────────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────────────────────────────

# Regex patterns
_TAG_LINE   = re.compile(r"^\[([a-z]:[a-z])\](?:\s+\{CRC:([0-9a-fA-F]{8})\})?$")
_DATA_LINE  = re.compile(r"^DATA:\s+(.+)$")
_CRC_LINE   = re.compile(r"^CRC:\s+([0-9a-fA-F]{8})$")
_FORK_OPEN  = re.compile(r"^FORK:$")
_PATH_HDR   = re.compile(r"^\s{2}PATH\s+([a-z]:[a-z]):$")
_FORK_CLOSE = re.compile(r"^ENDFORK$")
_COMMENT    = re.compile(r"^#(.*)$")
_HEADER     = re.compile(r"^LOM\s+v(\d+)\.(\d+)$")

def _crc32_hex(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"

def _validate_crc(data: bytes, crc_hex: Optional[str]) -> bool:
    if crc_hex is None:
        return True  # no CRC provided — skip validation
    return _crc32_hex(data) == crc_hex.lower()

class LotParser:
    """
    Parse a .lot text stream into a sequence of events.

    Usage:
        parser = LotParser(text)
        for event in parser.parse():
            ...
    """

    def __init__(self, text: str):
        self.lines   = text.splitlines()
        self.pos     = 0
        self._fork_counter = 0

    def _peek(self) -> Optional[str]:
        if self.pos < len(self.lines):
            return self.lines[self.pos]
        return None

    def _consume(self) -> Optional[str]:
        if self.pos < len(self.lines):
            line = self.lines[self.pos]
            self.pos += 1
            return line
        return None

    def _lineno(self) -> int:
        return self.pos

    def parse(self) -> Iterator:
        """Yield events from the stream."""
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            stripped = line.strip()

            if not stripped:
                self.pos += 1
                continue

            # Comment
            m = _COMMENT.match(stripped)
            if m:
                yield CommentEvent(m.group(1).strip(), self._lineno())
                self.pos += 1
                continue

            # Stream header
            m = _HEADER.match(stripped)
            if m:
                yield HeaderEvent((int(m.group(1)), int(m.group(2))), self._lineno())
                self.pos += 1
                continue

            # Fork block
            if _FORK_OPEN.match(stripped):
                self.pos += 1
                yield from self._parse_fork()
                continue

            # Routing tag
            m = _TAG_LINE.match(stripped)
            if m:
                tag_str, crc = m.group(1), m.group(2)
                tag = parse_tag(tag_str)
                if tag is None:
                    yield ErrorEvent(f"Unknown tag '{tag_str}'", self._lineno())
                else:
                    yield TagEvent(tag, crc, self._lineno())
                self.pos += 1
                continue

            # DATA line
            m = _DATA_LINE.match(stripped)
            if m:
                b64 = m.group(1).strip()
                try:
                    raw = base64.b64decode(b64)
                except Exception:
                    yield ErrorEvent(f"Bad base64 on line {self._lineno()}", self._lineno())
                    self.pos += 1
                    continue
                # Peek for CRC line
                self.pos += 1
                crc_hex = None
                if self.pos < len(self.lines):
                    next_stripped = self.lines[self.pos].strip()
                    cm = _CRC_LINE.match(next_stripped)
                    if cm:
                        crc_hex = cm.group(1)
                        self.pos += 1
                valid = _validate_crc(raw, crc_hex)
                if not valid:
                    yield ErrorEvent(f"CRC mismatch for DATA block near line {self._lineno()}", self._lineno())
                yield DataEvent(raw, crc_hex, self._lineno(), valid)
                continue

            # Unknown line
            yield ErrorEvent(f"Unrecognised line {self._lineno()}: {stripped!r}", self._lineno())
            self.pos += 1

    def _parse_fork(self) -> Iterator:
        """Parse a FORK: ... ENDFORK block."""
        self._fork_counter += 1
        fork_id = self._fork_counter
        lineno  = self._lineno()
        paths   = []
        fork_tag = parse_tag("f:k")  # default to FORK-LOCK

        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            stripped = line.strip()

            if _FORK_CLOSE.match(stripped):
                self.pos += 1
                break

            m = _PATH_HDR.match(line)
            if m:
                tag_str = m.group(1)
                path_tag = parse_tag(tag_str)
                self.pos += 1
                path_events = list(self._parse_path_body())
                if path_tag:
                    paths.append(ForkPath(path_tag, path_events))
                continue

            self.pos += 1  # skip unexpected lines inside fork

        yield ForkEvent(fork_id, fork_tag, paths, lineno)

    def _parse_path_body(self) -> Iterator:
        """Parse lines inside a PATH block until next PATH or ENDFORK."""
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            if _PATH_HDR.match(line) or _FORK_CLOSE.match(line.strip()):
                return
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                self.pos += 1
                continue

            m = _DATA_LINE.match(stripped)
            if m:
                b64 = m.group(1).strip()
                try:
                    raw = base64.b64decode(b64)
                except Exception:
                    raw = b""
                self.pos += 1
                crc_hex = None
                if self.pos < len(self.lines):
                    cm = _CRC_LINE.match(self.lines[self.pos].strip())
                    if cm:
                        crc_hex = cm.group(1)
                        self.pos += 1
                valid = _validate_crc(raw, crc_hex)
                yield DataEvent(raw, crc_hex, self.pos, valid)
                continue

            m = _TAG_LINE.match(stripped)
            if m:
                tag = parse_tag(m.group(1))
                if tag:
                    yield TagEvent(tag, m.group(2), self.pos)
                self.pos += 1
                continue

            # TEXT shorthand (unquoted text inside a PATH)
            if stripped and not stripped.startswith("["):
                raw = stripped.encode()
                yield DataEvent(raw, None, self.pos, True)
            self.pos += 1
