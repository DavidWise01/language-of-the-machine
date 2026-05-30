"""
mechane.py — Language of the Machine · LOT v1.0 Interpreter
μηχανή (mechane) = machine

The main entry point. Reads .lot streams, handles forks, delivers output.

Usage:
    python mechane.py <file.lot>               # interactive fork selection
    python mechane.py <file.lot> --path y:y    # auto-select y:y at every fork
    python mechane.py <file.lot> --path h:b    # auto-select h:b at every fork
    python mechane.py <file.lot> --dump        # dump all fork headers, no output
    python mechane.py <file.lot> --trace       # verbose trace of all events
    python mechane.py --list-tags              # print full tag vocabulary
    python mechane.py --spec                   # print schema summary
"""

import sys, os, argparse, textwrap
sys.path.insert(0, os.path.dirname(__file__))

from stoicheion import TAGS, STATES, ACTIONS, LOT_VERSION
from potamos    import LotParser, TagEvent, DataEvent, ForkEvent, ErrorEvent, CommentEvent, HeaderEvent
from schisma    import ForkManager

BANNER = r"""
  ██╗      ██████╗ ████████╗
  ██║     ██╔═══██╗╚══██╔══╝
  ██║     ██║   ██║   ██║
  ██║     ██║   ██║   ██║
  ███████╗╚██████╔╝   ██║
  ╚══════╝ ╚═════╝    ╚═╝
  Language of the Machine · v1.0
  y:y primary  ·  h:b sidecar  ·  f:k lock at fork
"""

# ─────────────────────────────────────────────────────────────────
#  INTERPRETER
# ─────────────────────────────────────────────────────────────────

class MechaneInterpreter:
    """
    Full LOT v1.0 stream interpreter.

    Modes:
      interactive   — pauses at each fork, prompts operator
      auto          — auto-selects a fixed path at every fork
      dump          — prints fork headers only, no payload output
      trace         — logs every event
    """

    def __init__(self,
                 source:      str,
                 interactive: bool = True,
                 auto_path:   str  = "y:y",
                 dump_only:   bool = False,
                 trace:       bool = False,
                 quiet:       bool = False):
        self.source      = source
        self.interactive = interactive
        self.auto_path   = auto_path
        self.dump_only   = dump_only
        self.trace       = trace
        self.quiet       = quiet
        self.fm          = ForkManager(interactive=interactive)
        self.output      = bytearray()
        self.errors      = []
        self.stats       = {"tags":0,"data_blocks":0,"forks":0,"errors":0,"bytes_yielded":0}

    def run(self) -> bytearray:
        """Parse and interpret the stream. Returns yielded payload."""
        parser = LotParser(self.source)
        events = list(parser.parse())
        self._process(events)
        return self.output

    def _process(self, events) -> None:
        i = 0
        while i < len(events):
            ev = events[i]

            if isinstance(ev, HeaderEvent):
                if self.trace:
                    self._log(f"HEADER  LOT v{ev.version[0]}.{ev.version[1]}")
                i += 1
                continue

            if isinstance(ev, CommentEvent):
                if self.trace:
                    self._log(f"COMMENT #{ev.text}")
                i += 1
                continue

            if isinstance(ev, ErrorEvent):
                self.errors.append(ev.message)
                self.stats["errors"] += 1
                self._log(f"[m:e] ERROR line {ev.lineno}: {ev.message}", force=True)
                i += 1
                continue

            if isinstance(ev, TagEvent):
                self.stats["tags"] += 1
                tag = ev.tag
                if self.trace:
                    self._log(f"TAG     [{tag.raw}]  {tag.name:20}  {tag.doc[:60]}")

                if tag.is_end:
                    self._log(f"[{tag.raw}] stream ends — {tag.name}", force=not self.quiet)
                    break

                i += 1
                continue

            if isinstance(ev, DataEvent):
                self.stats["data_blocks"] += 1
                if not ev.valid:
                    self.errors.append(f"CRC mismatch at line {ev.lineno}")
                    self._log(f"[m:e] CRC MISMATCH — block at line {ev.lineno} discarded", force=True)
                    i += 1
                    continue
                if self.trace:
                    preview = ev.raw[:40].decode("utf-8", errors="replace").replace("\n"," ")
                    self._log(f"DATA    {len(ev.raw)} bytes  {preview!r}")
                if not self.dump_only:
                    self.output.extend(ev.raw)
                    self.stats["bytes_yielded"] += len(ev.raw)
                i += 1
                continue

            if isinstance(ev, ForkEvent):
                self.stats["forks"] += 1
                self._log(f"\n[f:k] FORK #{ev.fork_id} — {len(ev.paths)} paths", force=True)
                frame = self.fm.push_fork(ev)

                if self.dump_only:
                    self.fm._dump_headers(frame)
                    self.fm.stack.pop()
                    i += 1
                    continue

                if self.interactive:
                    payload = self._interactive_fork(frame)
                else:
                    self._log(f"  auto-selecting [{self.auto_path}]", force=not self.quiet)
                    payload = self.fm.auto_choose(frame, self.auto_path)

                if payload is not None:
                    self.output.extend(payload)
                    self.stats["bytes_yielded"] += len(payload)
                i += 1
                continue

            i += 1

    def _interactive_fork(self, frame) -> bytes | None:
        """Present fork options and get operator input."""
        self.fm.present_fork(frame)
        while True:
            try:
                raw = input("  choose → ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  [x:x] Interrupted — defaulting to y:y")
                raw = "y:y"
            if raw in ("?", "help"):
                self._print_fork_help()
                continue
            result = self.fm.choose(frame, raw)
            if frame.decided:
                return result
            # If frame not decided (e.g. f:d dump), loop

    def _print_fork_help(self) -> None:
        print(textwrap.dedent("""
          FORK COMMANDS
          ─────────────
          y:y   follow the primary stream (yield path)
          h:b   pivot to the hidden sidecar (hold:branch)
          f:d   dump both fork headers — inspect without choosing
          m:m   attempt merge of both streams
          ?     this help
        """))

    def _log(self, msg: str, force: bool = False) -> None:
        if self.trace or force:
            print(f"  {msg}")

    def summary(self) -> str:
        s = self.stats
        lines = [
            "",
            "  ─── STREAM SUMMARY ─────────────────────────────────",
            f"  tags parsed:    {s['tags']}",
            f"  data blocks:    {s['data_blocks']}",
            f"  forks resolved: {s['forks']}",
            f"  errors:         {s['errors']}",
            f"  bytes yielded:  {s['bytes_yielded']}",
        ]
        if self.errors:
            lines.append(f"  error log:")
            for e in self.errors:
                lines.append(f"    · {e}")
        lines.append("  ────────────────────────────────────────────────────")
        return "\n".join(lines)

# ─────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────

def cmd_list_tags() -> None:
    print("\n  LOT v1.0 TAG VOCABULARY")
    print("  " + "─" * 60)
    cur_group = None
    for raw, tag in sorted(TAGS.items(), key=lambda x: x[1].group+x[0]):
        if tag.group != cur_group:
            cur_group = tag.group
            print(f"\n  GROUP {tag.group}")
        markers = []
        if tag.is_fork:  markers.append("FORK")
        if tag.is_end:   markers.append("END")
        if tag.is_hold:  markers.append("HOLD")
        mark = f"  [{', '.join(markers)}]" if markers else ""
        print(f"  [{raw}]  {tag.name:<22} {tag.doc[:55]}{mark}")
    print()

def cmd_spec() -> None:
    print(textwrap.dedent(f"""
      Language of the Machine · LOT v{LOT_VERSION[0]}.{LOT_VERSION[1]}
      ─────────────────────────────────────
      Tag format:    STATE:ACTION  (e.g. y:y, h:b, f:k)
      State symbols: {', '.join(sorted(STATES.keys()))}
      Action symbols: {', '.join(sorted(ACTIONS.keys()))}
      Known tags:    {len(TAGS)}

      Core fork protocol:
        [f:k]  → lock read head, present options
        [y:y]  → follow primary stream
        [h:b]  → buffer sidecar, hold on standby
        [m:m]  → attempt stream merge
        [e:t]  → end, clean terminate

      File format (.lot):
        LOM v1.0
        [TAG] {{CRC:hex8}}
        DATA: <base64>
        CRC: <hex8>
        FORK:
          PATH y:y:
            DATA: ...
          PATH h:b:
            DATA: ...
        ENDFORK
        [e:t]
    """))

def main() -> None:
    ap = argparse.ArgumentParser(
        prog="mechane",
        description="LOT v1.0 — Language of the Machine interpreter",
    )
    ap.add_argument("file",         nargs="?",  help=".lot file to read")
    ap.add_argument("--path",       default="", help="auto-select path at every fork (y:y | h:b | ...)")
    ap.add_argument("--dump",       action="store_true", help="dump fork headers only, no payload output")
    ap.add_argument("--trace",      action="store_true", help="verbose event trace")
    ap.add_argument("--quiet",      action="store_true", help="suppress banners and summaries")
    ap.add_argument("--out",        default="",  help="write yielded bytes to file instead of stdout")
    ap.add_argument("--list-tags",  action="store_true", help="print tag vocabulary")
    ap.add_argument("--spec",       action="store_true", help="print schema summary")
    args = ap.parse_args()

    if args.list_tags:
        cmd_list_tags()
        return
    if args.spec:
        cmd_spec()
        return

    if not args.quiet:
        print(BANNER)

    if not args.file:
        ap.print_help()
        return

    try:
        source = open(args.file, "r", encoding="utf-8").read()
    except FileNotFoundError:
        print(f"[m:e] File not found: {args.file}")
        sys.exit(1)

    interactive = not bool(args.path) and not args.dump
    interp = MechaneInterpreter(
        source=source,
        interactive=interactive,
        auto_path=args.path or "y:y",
        dump_only=args.dump,
        trace=args.trace,
        quiet=args.quiet,
    )

    result = interp.run()

    if not args.quiet:
        print(interp.summary())

    if result and not args.dump:
        if args.out:
            with open(args.out, "wb") as f:
                f.write(result)
            print(f"  output → {args.out}")
        else:
            print("\n  ─── YIELDED OUTPUT ─────────────────────────────────")
            try:
                print(result.decode("utf-8"))
            except UnicodeDecodeError:
                print(f"  <binary: {len(result)} bytes>")
                print(f"  hex: {result.hex()[:80]}{'...' if len(result)>40 else ''}")

if __name__ == "__main__":
    main()
