"""
schisma.py — Fork handler and path selector for LOT v1.0
σχίσμα (schisma) = split, fork, schism

Manages the fork stack, path selection, and sidecar buffering.
"""

import zlib
from dataclasses import dataclass, field
from typing import Optional
from potamos import ForkEvent, ForkPath, DataEvent

MAX_FORK_DEPTH = 8

class ForkStackOverflow(Exception):
    pass

class NoActivePath(Exception):
    pass

@dataclass
class PathState:
    tag_str:  str              # "y:y" or "h:b"
    buffer:   bytearray = field(default_factory=bytearray)
    active:   bool = False
    chosen:   bool = False

@dataclass
class ForkFrame:
    fork_id:  int
    paths:    list[PathState]
    decided:  bool = False
    chosen_index: int = -1

class ForkManager:
    """
    Maintains the fork stack and sidecar buffers.
    Handles path selection and stream merging.
    """

    def __init__(self, interactive: bool = True):
        self.stack:       list[ForkFrame] = []
        self.interactive: bool = interactive
        self.primary_buf: bytearray = bytearray()
        self._events:     list = []  # collected events for replay

    # ──────────────────────────────────────────────────────────────
    #  FORK HANDLING
    # ──────────────────────────────────────────────────────────────

    def push_fork(self, event: ForkEvent) -> ForkFrame:
        """Push a new fork onto the stack. Returns the frame."""
        if len(self.stack) >= MAX_FORK_DEPTH:
            raise ForkStackOverflow(f"Fork stack depth {MAX_FORK_DEPTH} exceeded")

        states = []
        for path in event.paths:
            # Collect data from path events
            buf = bytearray()
            for ev in path.events:
                if isinstance(ev, DataEvent) and ev.valid:
                    buf.extend(ev.raw)
            ps = PathState(
                tag_str=path.tag.raw,
                buffer=buf,
                active=(path.tag.raw == "y:y"),  # y:y is active by default
            )
            states.append(ps)

        frame = ForkFrame(fork_id=event.fork_id, paths=states)
        self.stack.append(frame)
        return frame

    def present_fork(self, frame: ForkFrame) -> None:
        """Print the fork decision box to stdout."""
        print()
        print("  ┌─ FORK LOCKED " + "─" * 45 + "┐")
        print(f"  │ fork id: {frame.fork_id:04d}    depth: {len(self.stack)}/{MAX_FORK_DEPTH}")
        print(f"  │ paths available: {len(frame.paths)}")
        print("  │")
        for i, ps in enumerate(frame.paths):
            marker = "▶ ACTIVE" if ps.active else "  parked"
            preview = ps.buffer[:40].decode("utf-8", errors="replace").replace("\n"," ")
            crc_val = f"{zlib.crc32(bytes(ps.buffer)) & 0xFFFFFFFF:08x}"
            print(f"  │  [{ps.tag_str}]  {marker}   CRC:{crc_val}   {len(ps.buffer)} bytes")
            print(f"  │          preview: {preview!r}")
        print("  │")
        print("  │  commands:  y:y  │  h:b  │  f:d (peek)  │  m:m (merge)  │  ? (help)")
        print("  └" + "─" * 58 + "┘")

    def choose(self, frame: ForkFrame, choice: str) -> Optional[bytes]:
        """
        Process operator choice. Returns chosen payload or None.
        choice: "y:y" | "h:b" | "f:d" | "m:m"
        """
        if choice == "f:d":
            self._dump_headers(frame)
            return None

        if choice == "m:m":
            return self._attempt_merge(frame)

        # Find matching path
        for i, ps in enumerate(frame.paths):
            if ps.tag_str == choice:
                frame.decided = True
                frame.chosen_index = i
                ps.chosen = True
                ps.active = True
                # Park the other paths
                for j, other in enumerate(frame.paths):
                    if j != i:
                        other.active = False
                self.stack.pop()
                return bytes(ps.buffer)

        print(f"  [schisma] Unknown choice '{choice}'. Valid: " + ", ".join(ps.tag_str for ps in frame.paths))
        return None

    def _dump_headers(self, frame: ForkFrame) -> None:
        """f:d — inspect fork headers without choosing."""
        print("\n  ── FORK DUMP (f:d) ─────────────────────────────────")
        for ps in frame.paths:
            crc_val = f"{zlib.crc32(bytes(ps.buffer)) & 0xFFFFFFFF:08x}"
            print(f"  PATH [{ps.tag_str}]  CRC:{crc_val}  {len(ps.buffer)} bytes")
            print(f"  content (hex):  {bytes(ps.buffer).hex()[:64]}{'...' if len(ps.buffer)>32 else ''}")
            try:
                print(f"  content (utf8): {ps.buffer.decode('utf-8', errors='replace')[:120]}")
            except Exception:
                pass
            print()

    def _attempt_merge(self, frame: ForkFrame) -> Optional[bytes]:
        """m:m — attempt to merge both paths."""
        if len(frame.paths) < 2:
            print("  [schisma][m:e] Not enough paths to merge")
            return None

        a = frame.paths[0].buffer
        b = frame.paths[1].buffer

        # Compatible if byte-identical (trivial merge) or a is prefix of b or vice versa
        if a == b:
            print("  [schisma][m:y] Streams are identical — merge trivial")
            frame.decided = True
            self.stack.pop()
            return bytes(a)

        if bytes(a).startswith(bytes(b)):
            print(f"  [schisma][m:y] Path {frame.paths[0].tag_str} is superset — yielding primary")
            frame.decided = True
            self.stack.pop()
            return bytes(a)

        if bytes(b).startswith(bytes(a)):
            print(f"  [schisma][m:y] Path {frame.paths[1].tag_str} is superset — yielding extended")
            frame.decided = True
            self.stack.pop()
            return bytes(b)

        print("  [schisma][m:e] Streams are incompatible — cannot merge. Both preserved.")
        print("  Choose manually: y:y | h:b")
        return None

    def auto_choose(self, frame: ForkFrame, choice: str = "y:y") -> Optional[bytes]:
        """Non-interactive: automatically choose a path."""
        return self.choose(frame, choice)
