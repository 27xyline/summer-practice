import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from box_geometry import (
    BoxParams,
    build_panels,
    segment_bounds,
    verify_assembly,
)
from dxf_writer import create_dxf_document, save_dxf_file


class BoxGeneratorTests(unittest.TestCase):
    def test_builds_electronics_box_parts(self):
        panels = build_panels(BoxParams())
        segments = []
        for panel in panels:
            segments.extend(panel.segments)

        self.assertEqual([panel.title for panel in panels], ["ElectronicsBox"])
        self.assertEqual(len(segments), 2864)
        self.assertEqual(sum(1 for segment in segments if segment.layer == "CUT"), 664)
        self.assertEqual(sum(1 for segment in segments if segment.layer == "HOLES"), 2200)

    def test_default_dxf_uses_line_geometry_only(self):
        doc = create_dxf_document(BoxParams())

        for entity in doc.modelspace():
            self.assertEqual(entity.dxftype(), "LINE")

    def test_dxf_has_no_text(self):
        doc = create_dxf_document(BoxParams())
        objects = []
        for item in doc.modelspace():
            objects.append(item.dxftype())

        self.assertEqual(doc.header["$INSUNITS"], 4)
        self.assertEqual(doc.dxfversion, "AC1032")
        self.assertIn("LINE", objects)
        self.assertNotIn("TEXT", objects)
        self.assertTrue(doc.layers.has_entry("CUT"))
        self.assertTrue(doc.layers.has_entry("HOLES"))
        self.assertFalse(doc.layers.has_entry("TEXT"))
        self.assertEqual(doc.layers.get("CUT").dxf.color, 7)
        self.assertEqual(doc.layers.get("HOLES").dxf.color, 5)

    def test_default_layout_fits_sheet(self):
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
        self.assertGreater(holes, 40)

    def test_dxf_writer_creates_parent_directories(self):
        params = BoxParams()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "nested"
            dxf_path = output_dir / "box.dxf"

            save_dxf_file(params, dxf_path)

            self.assertTrue(dxf_path.exists())

    def test_rejects_too_small_box(self):
        with self.assertRaises(ValueError):
            verify_assembly(BoxParams(30, 100, 100, 3))

    def test_rejects_too_large_layout(self):
        with self.assertRaises(ValueError):
            verify_assembly(BoxParams(140, 140, 140, 3))

    def test_no_double_cut_lines(self):
        lines = {}
        for panel in build_panels(BoxParams()):
            for segment in panel.segments:
                if segment.layer == "CUT":
                    x1, y1, x2, y2 = segment.values
                    p1 = (round(x1, 4), round(y1, 4))
                    p2 = (round(x2, 4), round(y2, 4))
                    key = tuple(sorted([p1, p2]))
                    lines[key] = lines.get(key, 0) + 1

        for count in lines.values():
            self.assertEqual(count, 1)

    def test_verifies_default_params(self):
        verify_assembly(BoxParams())


def joint_line_sizes(params):
    sizes = []
    min_size = max(0, params.finger_width - 0.2)
    max_size = params.finger_width + 0.2
    for panel in build_panels(params):
        for segment in panel.segments:
            if segment.layer != "CUT":
                continue
            x1, y1, x2, y2 = segment.values
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            length = None
            if dx < 0.001:
                length = dy
            elif dy < 0.001:
                length = dx

            if length is not None and min_size <= length <= max_size:
                sizes.append(length)

    return sizes


def rectangular_hole_sizes(params):
    hole_lines = []
    for panel in build_panels(params):
        for segment in panel.segments:
            if segment.layer == "HOLES":
                hole_lines.append(segment)

    sizes = []
    for component in line_components(hole_lines):
        if len(component) != 4:
            continue

        points = []
        degrees = {}
        axis_aligned = True
        for segment in component:
            x1, y1, x2, y2 = segment.values
            p1 = rounded_point(x1, y1)
            p2 = rounded_point(x2, y2)
            points.extend([p1, p2])
            degrees[p1] = degrees.get(p1, 0) + 1
            degrees[p2] = degrees.get(p2, 0) + 1
            if abs(x1 - x2) > 0.0001 and abs(y1 - y2) > 0.0001:
                axis_aligned = False

        if not axis_aligned or any(degree != 2 for degree in degrees.values()):
            continue

        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        if width > 1 and height > 1:
            sizes.append((width, height))

    return sizes


def line_components(segments):
    point_to_segments = {}
    for index, segment in enumerate(segments):
        x1, y1, x2, y2 = segment.values
        for point in [rounded_point(x1, y1), rounded_point(x2, y2)]:
            point_to_segments.setdefault(point, []).append(index)

    seen = set()
    components = []
    for index in range(len(segments)):
        if index in seen:
            continue

        stack = [index]
        seen.add(index)
        component = []
        while stack:
            current = stack.pop()
            component.append(segments[current])
            x1, y1, x2, y2 = segments[current].values
            for point in [rounded_point(x1, y1), rounded_point(x2, y2)]:
                for neighbor in point_to_segments[point]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
        components.append(component)

    return components


def rounded_point(x, y):
    return round(x, 6), round(y, 6)


if __name__ == "__main__":
    unittest.main()
