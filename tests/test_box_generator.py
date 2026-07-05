import unittest

from box_geometry import BoxParams, build_panels, segment_bounds, verify_assembly
from dxf_writer import create_dxf_document


class BoxGeneratorTests(unittest.TestCase):
    def test_reads_svg_panels(self):
        panels = build_panels(BoxParams())
        names = []
        for panel in panels:
            names.append(panel.title)

        self.assertEqual(len(panels), 7)
        self.assertIn("Top", names)
        self.assertIn("Bottom", names)
        self.assertIn("Wall 1", names)

    def test_dxf_has_layers_and_objects(self):
        doc = create_dxf_document(BoxParams())
        objects = []
        for item in doc.modelspace():
            objects.append(item.dxftype())

        self.assertEqual(doc.header["$INSUNITS"], 4)
        self.assertIn("LINE", objects)
        self.assertIn("TEXT", objects)
        self.assertTrue(doc.layers.has_entry("CUT"))
        self.assertTrue(doc.layers.has_entry("HOLES"))
        self.assertTrue(doc.layers.has_entry("TEXT"))

    def test_layout_size_is_like_svg(self):
        segments = []
        for panel in build_panels(BoxParams()):
            segments.extend(panel.segments)

        min_x, min_y, max_x, max_y = segment_bounds(segments)
        self.assertGreaterEqual(min_x, 0)
        self.assertGreaterEqual(min_y, 0)
        self.assertAlmostEqual(max_x - min_x, 201.9, places=1)
        self.assertAlmostEqual(max_y - min_y, 432.2, places=1)

    def test_has_cut_and_hole_lines(self):
        cut = 0
        holes = 0
        for panel in build_panels(BoxParams()):
            for segment in panel.segments:
                if segment.layer == "CUT":
                    cut += 1
                elif segment.layer == "HOLES":
                    holes += 1

        self.assertGreater(cut, 100)
        self.assertGreater(holes, 100)

    def test_no_double_cut_lines(self):
        lines = {}
        for panel in build_panels(BoxParams()):
            for segment in panel.segments:
                if segment.kind == "line":
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
