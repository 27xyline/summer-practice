from __future__ import annotations

from dataclasses import dataclass


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
        return self.inner_length + 2 * self.thickness

    @property
    def outer_width(self) -> float:
        return self.inner_width + 2 * self.thickness

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


@dataclass(frozen=True)
class Panel:
    title: str
    x: float
    y: float
    segments: list[Segment]


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


def verify_assembly(params: BoxParams) -> None:
    length = params.outer_length
    width = params.outer_width
    checks = [
        ("нижние шипы передней/задней стенки", bottom_tab_intervals(params, length), length),
        ("нижние шипы боковых стенок", bottom_tab_intervals(params, params.inner_width), params.inner_width),
        ("боковые шипы боковых стенок", vertical_tab_intervals(params), params.inner_height),
    ]

    for name, intervals, limit in checks:
        if not intervals:
            raise ValueError(f"Не удалось построить {name}.")
        for start, end in intervals:
            if start < 0 or end > limit or end <= start:
                raise ValueError(f"Некорректная геометрия соединения: {name}.")

    if params.slot_width >= min(length, width) / 4:
        raise ValueError("Паз получается слишком широким для выбранных габаритов.")


def build_panels(params: BoxParams) -> list[Panel]:
    validate_params(params)
    verify_assembly(params)

    gap = params.panel_gap
    length = params.outer_length
    width = params.outer_width
    height = params.inner_height
    side_width = params.inner_width

    panels = [
        Panel("Дно: пазы под стенки и монтажные отверстия", 0, 0, bottom_panel(params, 0, 0))
    ]

    front_y = width + gap + params.thickness
    panels.append(Panel("Передняя стенка: пазы под боковины", 0, front_y, front_back_wall_panel(params, 0, front_y)))
    panels.append(
        Panel(
            "Задняя стенка: пазы под боковины",
            length + gap,
            front_y,
            front_back_wall_panel(params, length + gap, front_y),
        )
    )

    side_y = front_y + height + params.thickness + gap
    panels.append(Panel("Левая боковина: нижние и боковые шипы", 0, side_y, side_wall_panel(params, 0, side_y)))
    right_side_x = side_width + gap + 2 * params.tab_depth
    panels.append(
        Panel(
            "Правая боковина: нижние и боковые шипы",
            right_side_x,
            side_y,
            side_wall_panel(params, right_side_x, side_y),
        )
    )

    if params.include_lid:
        lid_x = 2 * (side_width + gap + 2 * params.tab_depth)
        panels.append(Panel("Крышка", lid_x, side_y, lid_panel(params, lid_x, side_y)))

    return panels


def bottom_panel(params: BoxParams, x: float, y: float) -> list[Segment]:
    length = params.outer_length
    width = params.outer_width
    segments = rounded_rect_segments(x, y, length, width, params.corner_radius)
    front_tabs = bottom_tab_intervals(params, length)
    side_tabs = bottom_tab_intervals(params, params.inner_width)
    slot_w = params.slot_width

    add_slots(segments, x, y, front_tabs, "horizontal", params)
    add_slots(segments, x, y + width - slot_w, front_tabs, "horizontal", params)
    add_slots(segments, x, y + params.thickness, side_tabs, "vertical", params)
    add_slots(segments, x + length - slot_w, y + params.thickness, side_tabs, "vertical", params)
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
    segments = tabbed_panel_outline(params, x, y, length, height, bottom_tab_intervals(params, length))
    slot_w = params.slot_width

    for start, end in vertical_tab_intervals(params):
        slot_h = max(end - start - params.kerf, 3.0)
        slot_y = y + start + params.kerf / 2
        segments.extend(rect_segments(x, slot_y, slot_w, slot_h))
        segments.extend(rect_segments(x + length - slot_w, slot_y, slot_w, slot_h))

    add_wall_holes(segments, params, x, y, length, height)
    return segments


def side_wall_panel(params: BoxParams, x: float, y: float) -> list[Segment]:
    width = params.inner_width
    height = params.inner_height
    side_tabs = vertical_tab_intervals(params)
    segments = tabbed_panel_outline(
        params,
        x,
        y,
        width,
        height,
        bottom_tab_intervals(params, width),
        left_tabs=side_tabs,
        right_tabs=side_tabs,
    )
    add_wall_holes(segments, params, x, y, width, height)
    return segments


def add_wall_holes(segments: list[Segment], params: BoxParams, x: float, y: float, width: float, height: float) -> None:
    if width < 60 or height < 35:
        return

    r = params.hole_diameter / 2
    side_margin = max(params.thickness * 2, min(params.hole_margin, width / 5))
    top_margin = min(params.hole_margin, height / 4)
    segments.append(Segment("circle", (x + side_margin, y + height - top_margin, r)))
    segments.append(Segment("circle", (x + width - side_margin, y + height - top_margin, r)))


def add_slots(
    segments: list[Segment],
    x: float,
    y: float,
    intervals: list[tuple[float, float]],
    orientation: str,
    params: BoxParams,
) -> None:
    for start, end in intervals:
        slot_len = max(end - start - params.kerf, 3.0)
        offset = start + params.kerf / 2
        if orientation == "horizontal":
            segments.extend(rect_segments(x + offset, y, slot_len, params.slot_width))
        else:
            segments.extend(rect_segments(x, y + offset, params.slot_width, slot_len))


def add_mounting_holes(segments: list[Segment], params: BoxParams, x: float, y: float, width: float, height: float) -> None:
    r = params.hole_diameter / 2
    m = params.hole_margin
    for hx, hy in [(x + m, y + m), (x + width - m, y + m), (x + m, y + height - m), (x + width - m, y + height - m)]:
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
    points: list[tuple[float, float]] = [(x, y)]
    tab_depth = params.tab_depth
    cursor = 0.0

    for start, end in bottom_tabs:
        if start > cursor:
            points.append((x + start, y))
        points.extend([(x + start, y - tab_depth), (x + end, y - tab_depth), (x + end, y)])
        cursor = end

    if cursor < width:
        points.append((x + width, y))

    cursor = 0.0
    for start, end in right_tabs:
        if start > cursor:
            points.append((x + width, y + start))
        points.extend([(x + width + tab_depth, y + start), (x + width + tab_depth, y + end), (x + width, y + end)])
        cursor = end

    if cursor < height:
        points.append((x + width, y + height))

    points.append((x, y + height))

    cursor = height
    for start, end in reversed(left_tabs):
        if end < cursor:
            points.append((x, y + end))
        points.extend([(x - tab_depth, y + end), (x - tab_depth, y + start), (x, y + start)])
        cursor = start

    if cursor > 0:
        points.append((x, y))

    return polyline_segments(points)


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

    gap = (usable - count * tab_width) / (count - 1)
    starts = [margin + i * (tab_width + gap) for i in range(count)]
    return [(start, start + tab_width) for start in starts]


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


def polyline_segments(points: list[tuple[float, float]], layer: str = "CUT") -> list[Segment]:
    return [
        Segment("line", (points[i][0], points[i][1], points[i + 1][0], points[i + 1][1]), layer)
        for i in range(len(points) - 1)
    ]


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
