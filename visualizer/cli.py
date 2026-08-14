"""Point it at a repository, get one HTML file back.

    visualizer .                          structure only, no run
    visualizer . --trace scripts/demo.py  overlay a recorded run
    visualizer . --trace-self             record this tool reading that repo
"""

from __future__ import annotations

import argparse
import os
import sys

from . import analyze, manifest, page, render, tracing


def compose(root: str, manifest_path: str | None, trace=None):
    """Everything between reading the disk and holding a finished Scene."""
    modules = analyze.read(root)
    data = manifest.load(root, modules, manifest_path)
    scene = manifest.compose(root, modules, data, trace)
    return scene, render.levels(scene)


def build(root: str, manifest_path: str | None, trace=None) -> str:
    scene, levels = compose(root, manifest_path, trace)
    return page.build(scene, levels)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="visualizer", description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository to read")
    parser.add_argument("-o", "--out", default=None, help="output HTML file")
    parser.add_argument("-m", "--manifest", default=None, help="manifest to use")
    parser.add_argument("--trace", metavar="SCRIPT", help="record a run of SCRIPT")
    parser.add_argument(
        "--trace-self",
        action="store_true",
        help="record this tool's own run over the repository, then draw that run",
    )
    parser.add_argument("args", nargs="*", help="arguments for the traced script")
    opts = parser.parse_args(argv)

    root = os.path.abspath(opts.root)
    if not os.path.isdir(root):
        parser.error(f"{root} is not a directory")

    manifest_path = opts.manifest or manifest.find_manifest(root)

    trace = None
    if opts.trace:
        trace = tracing.record_script(root, opts.trace, opts.args)
    elif opts.trace_self:
        # Two passes, and the reason matters: the run being recorded has to
        # include the drawing, so the drawing cannot be the recorded pass.
        # It records build() rather than compose() so that the module which
        # writes the page is in the recording too — everything but the write.
        trace, _ = tracing.record(root, build, root, manifest_path, None)

    document = build(root, manifest_path, trace)

    out = opts.out or os.path.join(root, f"{os.path.basename(root)}.map.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(document)

    where = "manifest" if manifest_path else "directory layout"
    flow = f"{len(trace.hops)} recorded hops" if trace and not trace.empty else "static call graph"
    print(f"{out}  ·  grouped by {where}  ·  flow from {flow}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
