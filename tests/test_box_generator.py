import unittest

from box_geometry import BoxParams, build_panels, verify_assembly
from dxf_writer import create_dxf_document


class BoxGeneratorTests(unittest.TestCase):
    def test_builds_expected_panels(self):
        panels = build_panels(BoxParams())
        titles = []
        for panel in panels:
            titles.append(panel.title)

        self.assertEqual(len(panels), 6)
        self.assertIn("Дно: пазы под стенки и монтажные отверстия", titles)
        self.assertIn("Крышка", titles)

    def test_generates_dxf(self):
        document = create_dxf_document(BoxParams(thickness=3.0, kerf=0.12))
        entity_types = []
        for entity in document.modelspace():
            entity_types.append(entity.dxftype())

        self.assertEqual(document.header["$INSUNITS"], 4)
        self.assertIn("LINE", entity_types)
        self.assertIn("CIRCLE", entity_types)
        self.assertIn("ARC", entity_types)
        self.assertTrue(document.layers.has_entry("CUT"))

    def test_verifies_supported_thicknesses(self):
        params_list = [
            BoxParams(thickness=3.0, kerf=0.12),
            BoxParams(thickness=4.0, kerf=0.15),
        ]
        for params in params_list:
            verify_assembly(params)


if __name__ == "__main__":
    unittest.main()
