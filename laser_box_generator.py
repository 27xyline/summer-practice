from __future__ import annotations

import math
import tkinter as tk
import argparse
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_TITLE = "Генератор DXF монтажного короба"


@dataclass(frozen=True)
class BoxParams:
    inner_length: float = 120.0
    inner_width: float = 80.0
    inner_height: float = 50.0
    thickness: float = 3.0
    kerf: float = 0.12
    tab_width: float = 12.0
    hole_diameter: float = 4.0
    hole_margin: float = 10.0
    corner_radius: float = 3.0
    panel_gap: float = 12.0
    include_lid: bool = True
    label: str = "Монтажный короб"

    @property
    def outer_length(self) -> float:
        return self.inner_length + 2.0 * self.thickness

    @property
    def outer_width(self) -> float:
        return self.inner_width + 2.0 * self.thickness

    @property
    def slot_width(self) -> float:
        return self.thickness + self.kerf

    @property
    def tab_depth(self) -> float:
        return self.thickness - self.kerf * 0.5


@dataclass(frozen=True)
class Segment:
    kind: str
    values: tuple[float, ...]
    layer: str = "CUT"


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
            "\n".join(
                [
                    "0",
                    "CIRCLE",
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
                ]
            )
        )

    def arc(
        self,
        x: float,
        y: float,
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str = "CUT",
    ) -> None:
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

    def text(self, x: float, y: float, text: str, height: float = 4.0, layer: str = "ENGRAVE") -> None:
        safe_text = text.replace("\n", " ")[:120]
        self.entities.append(
            "\n".join(
                [
                    "0",
                    "TEXT",
                    "8",
                    layer,
                    "10",
                    fmt(x),
                    "20",
                    fmt(y),
                    "30",
                    "0",
                    "40",
                    fmt(height),
                    "1",
                    safe_text,
                ]
            )
        )

    def extend(self, segments: list[Segment]) -> None:
        for segment in segments:
            if segment.kind == "line":
                self.line(*segment.values, layer=segment.layer)
            elif segment.kind == "circle":
                self.circle(*segment.values, layer=segment.layer)
            elif segment.kind == "arc":
                self.arc(*segment.values, layer=segment.layer)
            else:
                raise ValueError(f"Unknown segment type: {segment.kind}")

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
                self._layers_table(),
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
    def _layers_table() -> str:
        layers = [
            ("CUT", 1),
            ("ENGRAVE", 5),
            ("INFO", 8),
        ]
        lines = ["0", "TABLE", "2", "LAYER", "70", str(len(layers))]
        for name, color in layers:
            lines.extend(["0", "LAYER", "2", name, "70", "0", "62", str(color), "6", "CONTINUOUS"])
        lines.extend(["0", "ENDTAB"])
        return "\n".join(lines)


def fmt(value: float) -> str:
    if abs(value) < 1e-9:
        value = 0.0
    return f"{value:.4f}".rstrip("0").rstrip(".")


def validate_params(params: BoxParams) -> None:
    if params.inner_length < 40 or params.inner_width < 30 or params.inner_height < 20:
        raise ValueError("Габариты слишком маленькие для устойчивого короба.")
    if params.thickness <= 0 or params.kerf < 0:
        raise ValueError("Толщина должна быть больше 0, а компенсация реза не может быть отрицательной.")
    if params.thickness > min(params.inner_length, params.inner_width, params.inner_height) / 3:
        raise ValueError("Толщина фанеры слишком велика относительно размеров короба.")
    if params.tab_width < 4:
        raise ValueError("Ширина шипа должна быть не меньше 4 мм.")
    if params.hole_diameter < 1 or params.hole_margin < params.hole_diameter:
        raise ValueError("Проверьте диаметр отверстий и отступ от края.")
    if params.corner_radius < 0:
        raise ValueError("Радиус скругления не может быть отрицательным.")


def generate_dxf(params: BoxParams) -> str:
    validate_params(params)
    verify_assembly(params)
    doc = DxfDocument()
    doc.text(0, -8, f"{params.label}; толщина {fmt(params.thickness)} мм; рез {fmt(params.kerf)} мм", 4, "INFO")

    for panel in build_panels(params):
        doc.text(panel["x"], panel["y"] - 7, panel["title"], 4, "INFO")
        doc.extend(panel["segments"])

    return doc.to_string()


def build_panels(params: BoxParams) -> list[dict[str, object]]:
    x0 = 0.0
    y0 = 0.0
    gap = params.panel_gap
    length = params.outer_length
    width = params.outer_width
    height = params.inner_height
    side_width = params.inner_width

    panels: list[dict[str, object]] = []

    panels.append(
        panel(
            "Дно: пазы под стенки и монтажные отверстия",
            x0,
            y0,
            bottom_panel(params, x0, y0),
        )
    )

    front_y = y0 + width + gap + params.thickness
    panels.append(panel("Передняя стенка: пазы под боковины", x0, front_y, front_back_wall_panel(params, x0, front_y)))
    panels.append(
        panel(
            "Задняя стенка: пазы под боковины",
            x0 + length + gap,
            front_y,
            front_back_wall_panel(params, x0 + length + gap, front_y),
        )
    )

    side_y = front_y + height + params.thickness + gap
    panels.append(panel("Левая боковина: нижние и боковые шипы", x0, side_y, side_wall_panel(params, x0, side_y)))
    panels.append(
        panel(
            "Правая боковина: нижние и боковые шипы",
            x0 + side_width + gap + 2 * params.tab_depth,
            side_y,
            side_wall_panel(params, x0 + side_width + gap + 2 * params.tab_depth, side_y),
        )
    )

    if params.include_lid:
        lid_x = x0 + 2 * (side_width + gap + 2 * params.tab_depth)
        panels.append(panel("Крышка", lid_x, side_y, lid_panel(params, lid_x, side_y)))

    return panels


def panel(title: str, x: float, y: float, segments: list[Segment]) -> dict[str, object]:
    return {"title": title, "x": x, "y": y, "segments": segments}


def bottom_panel(params: BoxParams, x: float, y: float) -> list[Segment]:
    length = params.outer_length
    width = params.outer_width
    segments = rounded_rect_segments(x, y, length, width, params.corner_radius)

    front_tabs = bottom_tab_intervals(params, length)
    side_tabs = bottom_tab_intervals(params, params.inner_width)
    slot_w = params.slot_width

    add_slots_from_intervals(
        segments,
        x,
        y,
        front_tabs,
        "horizontal",
        params,
    )
    add_slots_from_intervals(
        segments,
        x,
        y + width - slot_w,
        front_tabs,
        "horizontal",
        params,
    )
    add_slots_from_intervals(
        segments,
        x,
        y + params.thickness,
        side_tabs,
        "vertical",
        params,
    )
    add_slots_from_intervals(
        segments,
        x + length - slot_w,
        y + params.thickness,
        side_tabs,
        "vertical",
        params,
    )

    add_mounting_holes(segments, params, x, y, length, width)
    return segments


def lid_panel(params: BoxParams, x: float, y: float) -> list[Segment]:
    length = params.outer_length
    width = params.outer_width
    segments = rounded_rect_segments(x, y, length, width, params.corner_radius)
    add_mounting_holes(segments, params, x, y, length, width)
    add_finger_notch(segments, x + length / 2 - 10, y + width - 6, 20, 6)
    return segments


def front_back_wall_panel(params: BoxParams, x: float, y: float) -> list[Segment]:
    length = params.outer_length
    height = params.inner_height
    bottom_tabs = bottom_tab_intervals(params, length)
    side_tabs = vertical_tab_intervals(params)
    segments = tabbed_panel_outline(params, x, y, length, height, bottom_tabs)

    slot_w = params.slot_width
    left_slot_x = x
    right_slot_x = x + length - slot_w
    for start, end in side_tabs:
        slot_h = max(end - start - params.kerf, 3.0)
        slot_y = y + start + params.kerf / 2
        segments.extend(rect_segments(left_slot_x, slot_y, slot_w, slot_h))
        segments.extend(rect_segments(right_slot_x, slot_y, slot_w, slot_h))

    hole_r = params.hole_diameter / 2
    side_margin = max(params.thickness * 2, min(params.hole_margin, length / 5))
    top_margin = min(params.hole_margin, height / 4)
    if length >= 70 and height >= 35:
        segments.append(Segment("circle", (x + side_margin, y + height - top_margin, hole_r)))
        segments.append(Segment("circle", (x + length - side_margin, y + height - top_margin, hole_r)))
    return segments


def side_wall_panel(params: BoxParams, x: float, y: float) -> list[Segment]:
    width = params.inner_width
    height = params.inner_height
    bottom_tabs = bottom_tab_intervals(params, width)
    side_tabs = vertical_tab_intervals(params)
    segments = tabbed_panel_outline(
        params,
        x,
        y,
        width,
        height,
        bottom_tabs,
        left_tabs=side_tabs,
        right_tabs=side_tabs,
    )

    hole_r = params.hole_diameter / 2
    side_margin = max(params.thickness * 2, min(params.hole_margin, width / 5))
    top_margin = min(params.hole_margin, height / 4)
    if width >= 60 and height >= 35:
        segments.append(Segment("circle", (x + side_margin, y + height - top_margin, hole_r)))
        segments.append(Segment("circle", (x + width - side_margin, y + height - top_margin, hole_r)))
    return segments


def rounded_rect_segments(x: float, y: float, width: float, height: float, radius: float) -> list[Segment]:
    r = min(max(radius, 0.0), width / 2, height / 2)
    if r == 0:
        return rect_segments(x, y, width, height)

    return [
        Segment("line", (x + r, y, x + width - r, y)),
        Segment("arc", (x + width - r, y + r, r, 270, 360)),
        Segment("line", (x + width, y + r, x + width, y + height - r)),
        Segment("arc", (x + width - r, y + height - r, r, 0, 90)),
        Segment("line", (x + width - r, y + height, x + r, y + height)),
        Segment("arc", (x + r, y + height - r, r, 90, 180)),
        Segment("line", (x, y + height - r, x, y + r)),
        Segment("arc", (x + r, y + r, r, 180, 270)),
    ]


def rect_segments(x: float, y: float, width: float, height: float, layer: str = "CUT") -> list[Segment]:
    return [
        Segment("line", (x, y, x + width, y), layer),
        Segment("line", (x + width, y, x + width, y + height), layer),
        Segment("line", (x + width, y + height, x, y + height), layer),
        Segment("line", (x, y + height, x, y), layer),
    ]


def add_slots_from_intervals(
    segments: list[Segment],
    x: float,
    y: float,
    intervals: list[tuple[float, float]],
    orientation: str,
    params: BoxParams,
) -> None:
    slot_w = params.slot_width
    for start, end in intervals:
        slot_len = max(end - start - params.kerf, 3.0)
        offset = start + params.kerf / 2
        if orientation == "horizontal":
            segments.extend(rect_segments(x + offset, y, slot_len, slot_w))
        else:
            segments.extend(rect_segments(x, y + offset, slot_w, slot_len))


def add_mounting_holes(
    segments: list[Segment],
    params: BoxParams,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    r = params.hole_diameter / 2
    margin = params.hole_margin
    for hx, hy in [
        (x + margin, y + margin),
        (x + width - margin, y + margin),
        (x + margin, y + height - margin),
        (x + width - margin, y + height - margin),
    ]:
        segments.append(Segment("circle", (hx, hy, r)))


def add_finger_notch(segments: list[Segment], x: float, y: float, width: float, height: float) -> None:
    radius = height / 2
    segments.append(Segment("line", (x, y + height, x + width, y + height)))
    segments.append(Segment("arc", (x + width, y + radius, radius, 90, 270)))
    segments.append(Segment("line", (x + width, y, x, y)))
    segments.append(Segment("arc", (x, y + radius, radius, 270, 90)))


def tabbed_panel_outline(
    params: BoxParams,
    x: float,
    y: float,
    width: float,
    height: float,
    bottom_tabs: list[tuple[float, float]],
    left_tabs: list[tuple[float, float]] | None = None,
    right_tabs: list[tuple[float, float]] | None = None,
) -> list[Segment]:
    left_tabs = left_tabs or []
    right_tabs = right_tabs or []
    tab_depth = params.tab_depth
    points: list[tuple[float, float]] = [(x, y)]
    cursor = 0.0

    for start, end in bottom_tabs:
        if start > cursor:
            points.append((x + start, y))
        points.extend(
            [
                (x + start, y - tab_depth),
                (x + end, y - tab_depth),
                (x + end, y),
            ]
        )
        cursor = end

    if cursor < width:
        points.append((x + width, y))

    cursor = 0.0
    for start, end in right_tabs:
        if start > cursor:
            points.append((x + width, y + start))
        points.extend(
            [
                (x + width + tab_depth, y + start),
                (x + width + tab_depth, y + end),
                (x + width, y + end),
            ]
        )
        cursor = end

    if cursor < height:
        points.append((x + width, y + height))

    points.append((x, y + height))

    cursor = height
    for start, end in reversed(left_tabs):
        if end < cursor:
            points.append((x, y + end))
        points.extend(
            [
                (x - tab_depth, y + end),
                (x - tab_depth, y + start),
                (x, y + start),
            ]
        )
        cursor = start

    if cursor > 0:
        points.append((x, y))

    return polyline_segments(points)


def polyline_segments(points: list[tuple[float, float]], layer: str = "CUT") -> list[Segment]:
    return [
        Segment("line", (points[i][0], points[i][1], points[i + 1][0], points[i + 1][1]), layer)
        for i in range(len(points) - 1)
    ]


def bottom_tab_intervals(params: BoxParams, length: float) -> list[tuple[float, float]]:
    margin = max(params.thickness * 1.8, params.tab_width * 0.6)
    return tab_intervals(length, params.tab_width, margin)


def vertical_tab_intervals(params: BoxParams) -> list[tuple[float, float]]:
    margin = max(params.thickness * 2.0, params.tab_width * 0.75)
    return tab_intervals(params.inner_height, params.tab_width, margin)


def tab_intervals(length: float, tab_width: float, margin: float) -> list[tuple[float, float]]:
    usable = length - 2 * margin
    if usable < tab_width:
        center = length / 2
        half = min(tab_width / 2, length / 3)
        return [(center - half, center + half)]

    count = max(1, int(usable // (tab_width * 1.55)) + 1)
    count = min(count, 9)
    tab_width = min(tab_width, usable / count)
    if count == 1:
        start = (length - tab_width) / 2
        return [(start, start + tab_width)]
    else:
        gap = (usable - count * tab_width) / (count - 1)
        starts = [margin + i * (tab_width + gap) for i in range(count)]
        return [(start, start + tab_width) for start in starts]


def verify_assembly(params: BoxParams) -> None:
    length = params.outer_length
    width = params.outer_width
    slot_w = params.slot_width
    bottom_front = bottom_tab_intervals(params, length)
    side_bottom = bottom_tab_intervals(params, params.inner_width)
    side_vertical = vertical_tab_intervals(params)

    checks = [
        ("нижние шипы передней/задней стенки", bottom_front, length),
        ("нижние шипы боковых стенок", side_bottom, params.inner_width),
        ("боковые шипы боковых стенок", side_vertical, params.inner_height),
    ]
    for name, intervals, limit in checks:
        if not intervals:
            raise ValueError(f"Не удалось построить {name}.")
        for start, end in intervals:
            if start < 0 or end > limit or end <= start:
                raise ValueError(f"Некорректная геометрия соединения: {name}.")

    if params.thickness + params.kerf >= min(length, width) / 4:
        raise ValueError("Паз получается слишком широким для выбранных габаритов.")


class GeneratorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x760")
        self.minsize(980, 680)

        self.values: dict[str, tk.StringVar] = {
            "inner_length": tk.StringVar(value="120"),
            "inner_width": tk.StringVar(value="80"),
            "inner_height": tk.StringVar(value="50"),
            "thickness": tk.StringVar(value="3"),
            "kerf": tk.StringVar(value="0.12"),
            "tab_width": tk.StringVar(value="12"),
            "hole_diameter": tk.StringVar(value="4"),
            "hole_margin": tk.StringVar(value="10"),
            "corner_radius": tk.StringVar(value="3"),
            "panel_gap": tk.StringVar(value="12"),
            "label": tk.StringVar(value="Монтажный короб"),
        }
        self.include_lid = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Готово к генерации DXF.")

        self._build_layout()
        self.preview()

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        controls = ttk.Frame(root)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 14))

        preview_frame = ttk.Frame(root)
        preview_frame.grid(row=0, column=1, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        fields = [
            ("inner_length", "Внутренняя длина, мм"),
            ("inner_width", "Внутренняя ширина, мм"),
            ("inner_height", "Высота стенок, мм"),
            ("thickness", "Толщина фанеры, мм"),
            ("kerf", "Компенсация реза, мм"),
            ("tab_width", "Ширина шипа, мм"),
            ("hole_diameter", "Диаметр отверстий, мм"),
            ("hole_margin", "Отступ отверстий, мм"),
            ("corner_radius", "Скругление углов, мм"),
            ("panel_gap", "Зазор раскладки, мм"),
            ("label", "Подпись"),
        ]

        ttk.Label(controls, text=APP_TITLE, font=("TkDefaultFont", 15, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        for row, (key, label) in enumerate(fields, start=1):
            ttk.Label(controls, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(controls, textvariable=self.values[key], width=22)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            entry.bind("<KeyRelease>", lambda _event: self.preview())

        lid_row = len(fields) + 1
        ttk.Checkbutton(controls, text="Добавить крышку", variable=self.include_lid, command=self.preview).grid(
            row=lid_row, column=0, columnspan=2, sticky="w", pady=(8, 4)
        )

        btn_row = lid_row + 1
        ttk.Button(controls, text="Обновить предпросмотр", command=self.preview).grid(
            row=btn_row, column=0, columnspan=2, sticky="ew", pady=(12, 4)
        )
        ttk.Button(controls, text="Сохранить DXF", command=self.save_dxf).grid(
            row=btn_row + 1, column=0, columnspan=2, sticky="ew", pady=4
        )
        ttk.Button(controls, text="Пример 3 мм", command=lambda: self.set_thickness("3")).grid(
            row=btn_row + 2, column=0, sticky="ew", pady=4, padx=(0, 4)
        )
        ttk.Button(controls, text="Пример 4 мм", command=lambda: self.set_thickness("4")).grid(
            row=btn_row + 2, column=1, sticky="ew", pady=4
        )

        ttk.Label(controls, textvariable=self.status, wraplength=290, foreground="#255a77").grid(
            row=btn_row + 3, column=0, columnspan=2, sticky="w", pady=(14, 0)
        )

        self.canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=1, highlightbackground="#b8b8b8")
        self.canvas.grid(row=0, column=0, sticky="nsew")

    def current_params(self) -> BoxParams:
        numbers: dict[str, float] = {}
        for key in [
            "inner_length",
            "inner_width",
            "inner_height",
            "thickness",
            "kerf",
            "tab_width",
            "hole_diameter",
            "hole_margin",
            "corner_radius",
            "panel_gap",
        ]:
            numbers[key] = float(self.values[key].get().replace(",", "."))

        return BoxParams(
            inner_length=numbers["inner_length"],
            inner_width=numbers["inner_width"],
            inner_height=numbers["inner_height"],
            thickness=numbers["thickness"],
            kerf=numbers["kerf"],
            tab_width=numbers["tab_width"],
            hole_diameter=numbers["hole_diameter"],
            hole_margin=numbers["hole_margin"],
            corner_radius=numbers["corner_radius"],
            panel_gap=numbers["panel_gap"],
            include_lid=self.include_lid.get(),
            label=self.values["label"].get().strip() or "Монтажный короб",
        )

    def set_thickness(self, value: str) -> None:
        self.values["thickness"].set(value)
        self.preview()

    def save_dxf(self) -> None:
        try:
            params = self.current_params()
            dxf = generate_dxf(params)
        except Exception as exc:
            messagebox.showerror("Ошибка параметров", str(exc))
            return

        default_name = f"montazhny_korob_{fmt(params.thickness)}mm.dxf"
        path = filedialog.asksaveasfilename(
            title="Сохранить DXF",
            defaultextension=".dxf",
            initialfile=default_name,
            filetypes=[("DXF files", "*.dxf"), ("All files", "*.*")],
        )
        if not path:
            return

        Path(path).write_text(dxf, encoding="utf-8")
        self.status.set(f"DXF сохранён: {path}")

    def preview(self) -> None:
        try:
            params = self.current_params()
            validate_params(params)
            verify_assembly(params)
            panels = build_panels(params)
        except Exception as exc:
            self.status.set(f"Ошибка параметров: {exc}")
            return

        self.canvas.delete("all")
        segments: list[Segment] = []
        for item in panels:
            segments.extend(item["segments"])

        bounds = segment_bounds(segments)
        if not bounds:
            return
        min_x, min_y, max_x, max_y = bounds
        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        margin = 36
        scale = min((canvas_w - 2 * margin) / (max_x - min_x), (canvas_h - 2 * margin) / (max_y - min_y))
        if not math.isfinite(scale) or scale <= 0:
            scale = 1.0

        def map_point(px: float, py: float) -> tuple[float, float]:
            sx = margin + (px - min_x) * scale
            sy = canvas_h - margin - (py - min_y) * scale
            return sx, sy

        for item in panels:
            tx, ty = map_point(item["x"], item["y"] - 4)
            self.canvas.create_text(tx, ty, text=item["title"], anchor="sw", fill="#505050", font=("TkDefaultFont", 9))

        for segment in segments:
            if segment.kind == "line":
                x1, y1, x2, y2 = segment.values
                self.canvas.create_line(*map_point(x1, y1), *map_point(x2, y2), fill="#b20d0d", width=1.5)
            elif segment.kind == "circle":
                x, y, r = segment.values
                x1, y1 = map_point(x - r, y - r)
                x2, y2 = map_point(x + r, y + r)
                self.canvas.create_oval(x1, y1, x2, y2, outline="#b20d0d", width=1.5)
            elif segment.kind == "arc":
                x, y, r, start, extent_end = segment.values
                x1, y1 = map_point(x - r, y - r)
                x2, y2 = map_point(x + r, y + r)
                extent = extent_end - start
                if extent <= 0:
                    extent += 360
                self.canvas.create_arc(x1, y1, x2, y2, start=-start, extent=-extent, style=tk.ARC, outline="#b20d0d", width=1.5)

        self.status.set("Предпросмотр обновлён. Красные линии идут в слой CUT.")


def segment_bounds(segments: list[Segment]) -> tuple[float, float, float, float] | None:
    points: list[tuple[float, float]] = []
    for segment in segments:
        if segment.kind == "line":
            x1, y1, x2, y2 = segment.values
            points.extend([(x1, y1), (x2, y2)])
        elif segment.kind == "circle":
            x, y, r = segment.values
            points.extend([(x - r, y - r), (x + r, y + r)])
        elif segment.kind == "arc":
            x, y, r, *_ = segment.values
            points.extend([(x - r, y - r), (x + r, y + r)])

    if not points:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def write_example_files(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for thickness in (3.0, 4.0):
        params = BoxParams(thickness=thickness, kerf=0.12 if thickness == 3.0 else 0.15)
        path = output_dir / f"montazhny_korob_{fmt(thickness)}mm.dxf"
        path.write_text(generate_dxf(params), encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="GUI и DXF-генератор монтажного короба для лазерной резки.")
    parser.add_argument(
        "--examples",
        action="store_true",
        help="создать примерные DXF-файлы в output/dxf без запуска GUI",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="проверить согласование шипов и пазов для типовых толщин без запуска GUI",
    )
    args = parser.parse_args()

    if args.check:
        for thickness, kerf in [(3.0, 0.12), (4.0, 0.15)]:
            params = BoxParams(thickness=thickness, kerf=kerf)
            validate_params(params)
            verify_assembly(params)
            print(f"OK: {fmt(thickness)} мм, рез {fmt(kerf)} мм")
        return

    if args.examples:
        paths = write_example_files(Path("output/dxf"))
        for path in paths:
            print(path)
        return

    app = GeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
