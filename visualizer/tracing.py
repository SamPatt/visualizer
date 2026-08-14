"""Record a real run.

Static analysis says what *could* be called. This says what *did*. When a trace
is present the map stops being a picture of the file listing and becomes a
picture of one execution: block height is how often something was entered, and
TRACE ONE STEP walks hops that actually happened, in the order they happened.
"""

from __future__ import annotations

import os
import runpy
import sys
from dataclasses import dataclass, field

MAX_HOPS = 4000


@dataclass
class Trace:
    """Counts and an ordered hop list, both keyed by repo-relative module id."""

    counts: dict[str, int] = field(default_factory=dict)
    hops: list[tuple[str, str]] = field(default_factory=list)
    events: int = 0

    @property
    def empty(self) -> bool:
        return not self.counts


class Recorder:
    """A `sys.setprofile` hook that keeps only calls landing inside the repo."""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.trace = Trace()
        self._stack: list[str] = []
        self._prev: str | None = None

    def _module_of(self, filename: str) -> str | None:
        if not filename or filename.startswith("<"):
            return None
        path = os.path.abspath(filename)
        if not path.startswith(self.root + os.sep):
            return None
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def __call__(self, frame, event, arg) -> None:
        if event == "call":
            module = self._module_of(frame.f_code.co_filename)
            if module is None:
                return
            self.trace.events += 1
            self.trace.counts[module] = self.trace.counts.get(module, 0) + 1
            caller = self._stack[-1] if self._stack else None
            if caller and caller != module and len(self.trace.hops) < MAX_HOPS:
                self.trace.hops.append((caller, module))
            self._stack.append(module)
        elif event == "return":
            if self._stack and self._module_of(frame.f_code.co_filename) == self._stack[-1]:
                self._stack.pop()


def record(root: str, fn, *args, **kwargs) -> tuple[Trace, object]:
    """Run `fn` under the recorder and give back the trace and its result."""
    recorder = Recorder(root)
    sys.setprofile(recorder)
    try:
        result = fn(*args, **kwargs)
    finally:
        sys.setprofile(None)
    return recorder.trace, result


def record_script(root: str, script: str, argv: list[str]) -> Trace:
    """Run a script as `__main__` under the recorder.

    The script's own exit is caught: a traced run that calls sys.exit has still
    produced a usable trace, and losing it would be the wrong outcome.
    """
    script = os.path.abspath(script)
    saved_argv, saved_path = sys.argv[:], sys.path[:]
    sys.argv = [script, *argv]
    sys.path.insert(0, os.path.dirname(script))

    def run() -> None:
        try:
            runpy.run_path(script, run_name="__main__")
        except SystemExit:
            pass

    try:
        trace, _ = record(root, run)
    finally:
        sys.argv, sys.path = saved_argv, saved_path
    return trace


def compress(hops: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Collapse immediate repeats so the flow walks the shape, not the churn."""
    out: list[tuple[str, str]] = []
    for hop in hops:
        if not out or out[-1] != hop:
            out.append(hop)
    return out
