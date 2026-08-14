"""Checks for the claims the rest of the program makes about itself.

Run with `python -m unittest discover tests`. The repository is its own
fixture: the tool is pointed at the package it lives in.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from visualizer import analyze, cli, layout, manifest, model, render  # noqa: E402


class TestStaticReader(unittest.TestCase):
    def setUp(self):
        self.modules = analyze.read(ROOT)

    def test_reads_every_module(self):
        self.assertIn("visualizer/render.py", self.modules)
        self.assertGreater(self.modules["visualizer/render.py"].lines, 0)

    def test_relative_import_resolves_to_the_submodule(self):
        """`from . import layout` names a module, not the package __init__."""
        edges = {(src, dst) for src, dst, _ in analyze.call_edges(self.modules)}
        self.assertIn(("visualizer/render.py", "visualizer/layout.py"), edges)
        self.assertIn(("visualizer/render.py", "visualizer/iso.py"), edges)

    def test_call_sites_are_counted_not_just_imports(self):
        calls = self.modules["visualizer/render.py"].calls
        self.assertGreater(calls["visualizer/iso.py"], 1)

    def test_external_imports_are_not_edges(self):
        for module in self.modules.values():
            for target in module.calls:
                self.assertIn(target, self.modules)


class TestScene(unittest.TestCase):
    def setUp(self):
        self.modules = analyze.read(ROOT)
        self.data = manifest.load(ROOT, self.modules, manifest.find_manifest(ROOT))
        self.scene = manifest.compose(ROOT, self.modules, self.data)

    def test_manifest_is_used(self):
        self.assertEqual(self.scene.repo, "visualizer")
        self.assertTrue(self.scene.groups)

    def test_inner_ids_are_qualified_by_module(self):
        """Bare names collide: two modules here define `read`, two `_inside`."""
        seen = {}
        for node in self.scene.nodes:
            for inner in node.inside:
                self.assertNotIn(inner.id, seen, f"{inner.id} claimed twice")
                seen[inner.id] = node.id
                self.assertTrue(inner.id.startswith(node.id + "::"))
        self.assertIn("visualizer/analyze.py::read", seen)
        self.assertIn("visualizer/manifest.py::load", seen)

    def test_untraced_scene_says_so(self):
        self.assertFalse(self.scene.traced)
        self.assertEqual(self.scene.height_means, "lines of code")

    def test_optional_edges_are_dashed_without_a_recording(self):
        optional = [e for e in self.scene.edges if e.dst.endswith("tracing.py")]
        self.assertTrue(optional)
        for edge in optional:
            self.assertEqual(edge.kind, model.DASHED)

    def test_no_manifest_falls_back_to_the_layout(self):
        scene = manifest.compose(ROOT, self.modules, manifest.load(ROOT, self.modules, None))
        self.assertTrue(scene.nodes)
        self.assertTrue(any("layout" in s.body.lower() for s in scene.what))


class TestLayout(unittest.TestCase):
    def setUp(self):
        modules = analyze.read(ROOT)
        data = manifest.load(ROOT, modules, manifest.find_manifest(ROOT))
        self.scene = manifest.compose(ROOT, modules, data)
        layout.place(self.scene)

    def test_every_node_is_placed(self):
        for node in self.scene.nodes:
            self.assertIsNotNone(node.pos)

    def test_footprints_do_not_overlap(self):
        rects = [layout._rect(n) for n in self.scene.nodes]
        for i, (ax0, ay0, ax1, ay1) in enumerate(rects):
            for bx0, by0, bx1, by1 in rects[i + 1 :]:
                overlap = ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1
                self.assertFalse(overlap, "two blocks share ground")

    def test_routes_avoid_the_blocks_they_do_not_touch(self):
        paths = layout.route(self.scene)
        self.assertTrue(paths)
        by_id = {n.id: n for n in self.scene.nodes}
        for (src, dst), path in paths.items():
            others = [n for n in self.scene.nodes if n.id not in (src, dst)]
            for i in range(len(path) - 1):
                (ax, ay), (bx, by) = path[i], path[i + 1]
                for step in range(21):
                    t = step / 20
                    point = (ax + (bx - ax) * t, ay + (by - ay) * t)
                    for node in others:
                        x0, y0, x1, y1 = layout._rect(node)
                        strictly_inside = (
                            x0 < point[0] < x1 and y0 < point[1] < y1
                        )
                        self.assertFalse(
                            strictly_inside,
                            f"{src}->{dst} crosses {node.id}",
                        )

    def test_height_never_runs_away_from_the_footprint(self):
        heights = layout.assign_heights(self.scene.nodes)
        for node in self.scene.nodes:
            self.assertLessEqual(heights[node.id], 1.25 * min(node.size) + 1e-9)


class TestPage(unittest.TestCase):
    def setUp(self):
        self.html = cli.build(ROOT, manifest.find_manifest(ROOT))
        marker = "window.__MAP__ = "
        start = self.html.index(marker) + len(marker)
        self.payload, _ = json.JSONDecoder().raw_decode(self.html[start:])

    def test_output_is_one_self_contained_file(self):
        self.assertNotIn("<script src", self.html)
        self.assertNotIn("<link rel=\"stylesheet\"", self.html)
        self.assertNotIn("http://", self.html.split("xmlns")[0])

    def test_every_hop_has_a_path_to_animate(self):
        """The flow silently does nothing if these keys drift apart."""
        for name, level in self.payload["levels"].items():
            self.assertTrue(
                all(render.key(a, b) in level["paths"] for a, b in level["hops"]),
                f"level {name!r} has a hop with no path",
            )
        self.assertTrue(self.payload["levels"][""]["hops"])

    def test_edge_key_separator_reaches_the_page(self):
        self.assertEqual(self.payload["sep"], render.EDGE_SEP)

    def test_every_block_on_the_plane_has_a_description(self):
        for name, level in self.payload["levels"].items():
            for node_id in level["order"]:
                self.assertIn(node_id, self.payload["nodes"])
                self.assertTrue(self.payload["nodes"][node_id]["what"])

    def test_only_two_colours(self):
        found = set(__import__("re").findall(r"#[0-9A-Fa-f]{6}", self.html))
        self.assertLessEqual(found, {"#CDC499", "#000000"}, f"stray colour: {found}")


class TestRecording(unittest.TestCase):
    def test_recorded_run_changes_what_height_means(self):
        from visualizer import tracing

        trace, _ = tracing.record(ROOT, cli.compose, ROOT, manifest.find_manifest(ROOT), None)
        self.assertFalse(trace.empty)
        modules = analyze.read(ROOT)
        data = manifest.load(ROOT, modules, manifest.find_manifest(ROOT))
        scene = manifest.compose(ROOT, modules, data, trace)
        self.assertTrue(scene.traced)
        self.assertEqual(scene.height_means, "calls recorded")
        self.assertTrue(scene.hops)
        # the recorder cannot appear in its own recording
        recorder = scene.node("visualizer/tracing.py")
        self.assertEqual(recorder.calls, 0)

    def test_hops_are_real_pairs_of_known_blocks(self):
        from visualizer import tracing

        trace, _ = tracing.record(ROOT, cli.compose, ROOT, manifest.find_manifest(ROOT), None)
        modules = analyze.read(ROOT)
        data = manifest.load(ROOT, modules, manifest.find_manifest(ROOT))
        scene = manifest.compose(ROOT, modules, data, trace)
        known = {n.id for n in scene.nodes}
        for src, dst in scene.hops:
            self.assertIn(src, known)
            self.assertIn(dst, known)
            self.assertNotEqual(src, dst)


if __name__ == "__main__":
    unittest.main()
