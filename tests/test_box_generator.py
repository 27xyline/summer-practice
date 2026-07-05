import unittest

from box_geometry import BoxParams, build_panels, joint_line_sizes, rectangular_hole_sizes, segment_bounds, verify_assembly
from dxf_writer import create_dxf_document


class BoxGeneratorTests(unittest.TestCase):
    def test_builds_electronics_box_parts(self):
        panels = build_panels(BoxParams())

        self.assertEqual(len(panels), 7)
        self.assertGreater(sum(len(panel.segments) for panel in panels), 2500)

    def test_dxf_has_no_text(self):
        doc = create_dxf_document(BoxParams())
        objects = []
        for item in doc.modelspace():
            objects.append(item.dxftype())

        self.assertEqual(doc.header["$INSUNITS"], 4)
        self.assertIn("LINE", objects)
        self.assertNotIn("TEXT", objects)
        self.assertTrue(doc.layers.has_entry("CUT"))
        self.assertTrue(doc.layers.has_entry("HOLES"))
        self.assertFalse(doc.layers.has_entry("TEXT"))

    def test_default_layout_is_like_electronics_box_svg(self):
        params = BoxParams()
        segments = []
        for panel in build_panels(params):
            segments.extend(panel.segments)

        min_x, min_y, max_x, max_y = segment_bounds(segments)
        self.assertGreaterEqual(min_x, 0)
        self.assertGreaterEqual(min_y, 0)
        self.assertLessEqual(max_x - min_x, params.sheet_width)
        self.assertLessEqual(max_y - min_y, params.sheet_height)
        self.assertAlmostEqual(max_x - min_x, 201.5, places=1)
        self.assertAlmostEqual(max_y - min_y, 431, places=1)

    def test_can_change_size_and_thickness(self):
        for params in [BoxParams(80, 70, 60, 4), BoxParams(100, 100, 100, 4)]:
            verify_assembly(params)
            segments = []
            for panel in build_panels(params):
                segments.extend(panel.segments)

            min_x, min_y, max_x, max_y = segment_bounds(segments)
            self.assertLessEqual(max_x - min_x, params.sheet_width)
            self.assertLessEqual(max_y - min_y, params.sheet_height)

    def test_slots_match_teeth(self):
        params = BoxParams()
        sizes = rectangular_hole_sizes(params)
        expected = sorted([round(params.finger_width, 1), round(params.thickness, 1)])
        found = 0

        for width, height in sizes:
            current = sorted([round(width, 1), round(height, 1)])
            if current == expected:
                found += 1

        self.assertGreater(found, 10)
        self.assertEqual(expected, [3.0, 6.0])

    def test_finger_joints_use_nominal_width(self):
        params = BoxParams()
        sizes = [round(size, 1) for size in joint_line_sizes(params)]

        self.assertIn(6.0, sizes)
        self.assertNotIn(5.9, sizes)
        self.assertNotIn(6.1, sizes)
        self.assertGreater(sizes.count(round(params.finger_width, 1)), 10)

    def test_has_cut_and_hole_geometry(self):
        cut = 0
        holes = 0
        for panel in build_panels(BoxParams()):
            for segment in panel.segments:
                if segment.layer == "CUT":
                    cut += 1
                elif segment.layer == "HOLES":
                    holes += 1

        self.assertGreater(cut, 500)
        self.assertGreater(holes, 100)

    def test_rejects_too_small_box(self):
        with self.assertRaises(ValueError):
            verify_assembly(BoxParams(30, 100, 100, 3))

    def test_rejects_too_large_layout(self):
        with self.assertRaises(ValueError):
            verify_assembly(BoxParams(140, 140, 140, 3))

    def test_rejects_clearance(self):
        with self.assertRaises(ValueError):
            verify_assembly(BoxParams(clearance=0.1))

    def test_no_double_cut_lines(self):
        lines = {}
        for panel in build_panels(BoxParams()):
            for segment in panel.segments:
                if segment.layer == "CUT" and segment.kind == "line":
                    x1, y1, x2, y2 = segment.values
                    p1 = (round(x1, 4), round(y1, 4))
                    p2 = (round(x2, 4), round(y2, 4))
                    key = tuple(sorted([p1, p2]))
                    lines[key] = lines.get(key, 0) + 1

        for count in lines.values():
            self.assertEqual(count, 1)

    def test_verifies_template(self):
        verify_assembly(BoxParams())


if __name__ == "__main__":
    unittest.main()
