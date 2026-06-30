from __future__ import annotations

from pathlib import Path

from box_geometry import BoxParams, Segment, build_panels, fmt, validate_params, verify_assembly


class DxfDocument:
    def __init__(self) -> None:
        self.entities: list[str] = []

    def line(self, x1: float, y1: float, x2: float, y2: float, layer: str = "CUT") -> None:
        self.entities.append(
            "\n".join(
                [
                    "0",
                    "LINE",
                    "8",
                    layer,
                    "10",
                    fmt(x1),
                    "20",
                    fmt(y1),
                    "30",
                    "0",
                    "11",
                    fmt(x2),
                    "21",
                    fmt(y2),
                    "31",
                    "0",
                ]
            )
        )

    def circle(self, x: float, y: float, radius: float, layer: str = "CUT") -> None:
        self.entities.append(
            "\n".join(["0", "CIRCLE", "8", layer, "10", fmt(x), "20", fmt(y), "30", "0", "40", fmt(radius)])
        )

    def arc(self, x: float, y: float, radius: float, start_angle: float, end_angle: float, layer: str = "CUT") -> None:
        self.entities.append(
            "\n".join(
                [
                    "0",
                    "ARC",
                    "8",
                    layer,
                    "10",
                    fmt(x),
                    "20",
                    fmt(y),
                    "30",
                    "0",
                    "40",
                    fmt(radius),
                    "50",
                    fmt(start_angle),
                    "51",
                    fmt(end_angle),
                ]
            )
        )

    def add_segments(self, segments: list[Segment]) -> None:
        for segment in segments:
            if segment.kind == "line":
                self.line(*segment.values, layer=segment.layer)
            elif segment.kind == "circle":
                self.circle(*segment.values, layer=segment.layer)
            elif segment.kind == "arc":
                self.arc(*segment.values, layer=segment.layer)
            else:
                raise ValueError(f"Неизвестный тип линии: {segment.kind}")

    def to_string(self) -> str:
        return "\n".join(
            [
                "0",
                "SECTION",
                "2",
                "HEADER",
                "9",
                "$INSUNITS",
                "70",
                "4",
                "0",
                "ENDSEC",
                "0",
                "SECTION",
                "2",
                "TABLES",
                self.layers_table(),
                "0",
                "ENDSEC",
                "0",
                "SECTION",
                "2",
                "ENTITIES",
                *self.entities,
                "0",
                "ENDSEC",
                "0",
                "EOF",
                "",
            ]
        )

    @staticmethod
    def layers_table() -> str:
        layers = [("CUT", 1)]
        lines = ["0", "TABLE", "2", "LAYER", "70", str(len(layers))]
        for name, color in layers:
            lines.extend(["0", "LAYER", "2", name, "70", "0", "62", str(color), "6", "CONTINUOUS"])
        lines.extend(["0", "ENDTAB"])
        return "\n".join(lines)


def generate_dxf(params: BoxParams) -> str:
    validate_params(params)
    verify_assembly(params)

    doc = DxfDocument()
    for panel in build_panels(params):
        doc.add_segments(panel.segments)

    return doc.to_string()


def write_example_files(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for thickness, kerf in [(3.0, 0.12), (4.0, 0.15)]:
        params = BoxParams(thickness=thickness, kerf=kerf)
        path = output_dir / f"montazhny_korob_{fmt(thickness)}mm.dxf"
        path.write_text(generate_dxf(params), encoding="utf-8")
        paths.append(path)
    return paths
