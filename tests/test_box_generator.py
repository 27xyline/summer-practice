from __future__ import annotations

import unittest

from box_geometry import BoxParams, build_panels, verify_assembly
from dxf_writer import generate_dxf


class BoxGeneratorTests(unittest.TestCase):
    def test_builds_expected_panels(self) -> None:
        panels = build_panels(BoxParams())
        titles = [panel.title for panel in panels]

        self.assertEqual(len(panels), 6)
        self.assertIn("Дно: пазы под стенки и монтажные отверстия", titles)
        self.assertIn("Крышка", titles)

    def test_generates_dxf(self) -> None:
        dxf = generate_dxf(BoxParams(thickness=3.0, kerf=0.12))

        self.assertTrue(dxf.endswith("EOF\n"))
        self.assertIn("\nLINE\n", dxf)
        self.assertIn("\nCIRCLE\n", dxf)
        self.assertIn("\nARC\n", dxf)
        self.assertIn("CUT", dxf)

    def test_verifies_supported_thicknesses(self) -> None:
        for params in [BoxParams(thickness=3.0, kerf=0.12), BoxParams(thickness=4.0, kerf=0.15)]:
            with self.subTest(thickness=params.thickness):
                verify_assembly(params)


if __name__ == "__main__":
    unittest.main()
