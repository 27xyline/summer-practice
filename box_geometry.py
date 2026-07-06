import math
from dataclasses import dataclass


Point = tuple[float, float]
Contour = list[Point]
LayeredContour = tuple[str, Contour]

STANDARD_PARAMS = (100.0, 100.0, 100.0, 3.0, 6.0)
CIRCLE_STEPS = 176
CORNER_STEPS = 48


@dataclass
class BoxParams:
    length: float = 100
    depth: float = 100
    height: float = 100
    thickness: float = 3
    finger_width: float = 6
    sheet_width: float = 230
    sheet_height: float = 460

    def __post_init__(self):
        self.length = float(self.length)
        self.depth = float(self.depth)
        self.height = float(self.height)
        self.thickness = float(self.thickness)
        self.finger_width = float(self.finger_width)
        self.sheet_width = float(self.sheet_width)
        self.sheet_height = float(self.sheet_height)


@dataclass(frozen=True)
class Segment:
    start: Point
    end: Point
    layer: str = "CUT"

    @property
    def values(self):
        x1, y1 = self.start
        x2, y2 = self.end
        return x1, y1, x2, y2


@dataclass(frozen=True)
class Panel:
    title: str
    x: float
    y: float
    segments: list[Segment]


def fmt(value):
    return f"{value:.1f}".rstrip("0").rstrip(".")


def validate_params(params):
    values = [
        ("Длина", params.length),
        ("Глубина", params.depth),
        ("Высота", params.height),
        ("Толщина материала", params.thickness),
        ("Ширина шипа", params.finger_width),
        ("Ширина листа", params.sheet_width),
        ("Высота листа", params.sheet_height),
    ]

    for name, value in values:
        if not math.isfinite(value):
            raise ValueError(f"{name} указана неправильно")

    for name, value in values:
        if value <= 0:
            raise ValueError(f"{name} должна быть положительным числом")

    if params.thickness < 2 or params.thickness > 6:
        raise ValueError("Толщина материала должна быть от 2 до 6 мм")
    if params.finger_width < params.thickness or params.finger_width > 20:
        raise ValueError("Ширина шипа должна быть от толщины материала до 20 мм")

    min_side = max(45, params.thickness * 12, params.finger_width * 5)
    min_height = max(35, params.thickness * 10, params.finger_width * 5)
    if params.length < min_side:
        raise ValueError(f"Длина должна быть не меньше {fmt(min_side)} мм")
    if params.depth < min_side:
        raise ValueError(f"Глубина должна быть не меньше {fmt(min_side)} мм")
    if params.height < min_height:
        raise ValueError(f"Высота должна быть не меньше {fmt(min_height)} мм")


def verify_assembly(params):
    validate_params(params)
    panels = build_panels(params)
    segments = [segment for panel in panels for segment in panel.segments]
    bounds = segment_bounds(segments)
    if bounds is None:
        raise ValueError("В чертеже нет линий")

    min_x, min_y, max_x, max_y = bounds
    if min_x < -0.001 or min_y < -0.001:
        raise ValueError("Чертеж выходит в отрицательные координаты")

    layout_w = max_x - min_x
    layout_h = max_y - min_y
    if layout_w > params.sheet_width + 0.001:
        raise ValueError(f"Раскладка шире листа: {fmt(layout_w)} мм > {fmt(params.sheet_width)} мм")
    if layout_h > params.sheet_height + 0.001:
        raise ValueError(f"Раскладка выше листа: {fmt(layout_h)} мм > {fmt(params.sheet_height)} мм")


def build_panels(params):
    validate_params(params)
    if is_standard_box(params):
        segments = contours_to_segments(standard_box_contours())
        return [Panel("ElectronicsBox", 0, 0, segments)]
    return build_generated_panels(params)


def is_standard_box(params):
    values = (
        params.length,
        params.depth,
        params.height,
        params.thickness,
        params.finger_width,
    )
    return all(abs(value - expected) < 0.0001 for value, expected in zip(values, STANDARD_PARAMS))


def standard_box_contours():
    contours: list[LayeredContour] = []
    for x, y, style in [
        (10.0, 10.0, "outer"),
        (111.5, 10.0, "inner"),
        (111.5, 111.5, "inner"),
        (10.0, 111.5, "outer"),
    ]:
        contours.extend(wall_contours(x, y, style))

    contours.extend(base_contours())
    contours.extend(lid_contours())
    return contours


def wall_contours(x, y, style):
    contours = [
        ("HOLES", rect_contour(x + 12.5, y + 94.0, 6.0, 3.0)),
        ("HOLES", rect_contour(x + 81.5, y + 94.0, 6.0, 3.0)),
        ("CUT", wall_outline(x, y, style)),
    ]
    return contours


def wall_outline(x, y, style):
    t = 3.0
    w = 100.0
    h = 100.0
    points = [(x + t, y + t), (x + 11.0, y + t)]

    for current_x in range(11, 84, 12):
        points.extend(
            [
                (x + current_x, y),
                (x + current_x + 6.0, y),
                (x + current_x + 6.0, y + t),
                (x + current_x + 12.0, y + t),
            ]
        )
    points[-1] = (x + w - t, y + t)

    if style == "outer":
        points.append((x + w, y + t))
        points.extend(wall_side_points(x + w, x + w - t, y, h, "down"))
        points.extend([(x + t, y + h), (x, y + h)])
        points.extend(wall_side_points(x, x + t, y, h, "up"))
    else:
        points.extend(wall_side_points(x + w - t, x + w, y, h, "down"))
        points.append((x + t, y + h))
        points.extend(wall_side_points(x + t, x, y, h, "up"))

    return points


def wall_side_points(edge_x, notch_x, y, height, direction):
    if direction == "down":
        offsets = [12.5, 24.5, 36.5, 48.5, 60.5, 72.5, 84.5]
        points = []
        for offset in offsets:
            points.extend(
                [
                    (edge_x, y + offset),
                    (notch_x, y + offset),
                    (notch_x, y + offset + 6.0),
                    (edge_x, y + offset + 6.0),
                ]
            )
        points.append((edge_x, y + height))
        if abs(edge_x - notch_x) == 3.0 and edge_x > notch_x:
            points.append((notch_x, y + height))
        return points

    points = []
    for offset in [90.5, 78.5, 66.5, 54.5, 42.5, 30.5, 18.5]:
        points.extend(
            [
                (edge_x, y + offset),
                (notch_x, y + offset),
                (notch_x, y + offset - 6.0),
                (edge_x, y + offset - 6.0),
            ]
        )
    if edge_x < notch_x:
        points.extend([(edge_x, y + 3.0), (notch_x, y + 3.0)])
    else:
        points.append((edge_x, y + 3.0))
    return points


def base_contours():
    contours = [
        ("HOLES", circle_contour(17.0, 220.0, 1.5, 0.0)),
        ("CUT", rounded_base_outline()),
        ("HOLES", circle_contour(131.0, 220.0, 1.5, 90.0)),
    ]

    for slot_y in [224.0, 236.0, 248.0, 260.0, 272.0, 284.0, 296.0]:
        contours.append(("HOLES", rect_contour(121.0, slot_y, 3.0, 6.0)))

    contours.extend(
        [
            ("HOLES", circle_contour(131.0, 306.0, 1.5, 180.0)),
            ("HOLES", circle_contour(17.0, 306.0, 1.5, -90.0)),
        ]
    )

    for slot_y in [296.0, 284.0, 272.0, 260.0, 248.0, 236.0, 224.0]:
        contours.append(("HOLES", rect_contour(24.0, slot_y, 3.0, 6.0)))

    return contours


def rounded_base_outline():
    points = [(17.0, 213.0), (27.0, 213.0), (35.0, 213.0)]
    for current_x in range(35, 108, 12):
        points.extend(
            [
                (current_x, 216.0),
                (current_x + 6.0, 216.0),
                (current_x + 6.0, 213.0),
                (current_x + 12.0, 213.0),
            ]
        )
    points[-1] = (121.0, 213.0)
    points.append((131.0, 213.0))
    points.extend(arc_points(131.0, 220.0, 7.0, -90.0, 0.0)[1:])
    points.append((138.0, 306.0))
    points.extend(arc_points(131.0, 306.0, 7.0, 0.0, 90.0)[1:])
    points.extend([(121.0, 313.0), (113.0, 313.0)])
    for current_x in range(113, 34, -12):
        points.extend(
            [
                (current_x, 310.0),
                (current_x - 6.0, 310.0),
                (current_x - 6.0, 313.0),
                (current_x - 12.0, 313.0),
            ]
        )
    points[-1] = (27.0, 313.0)
    points.append((17.0, 313.0))
    points.extend(arc_points(17.0, 306.0, 7.0, 90.0, 180.0)[1:])
    points.append((10.0, 220.0))
    points.extend(arc_points(17.0, 220.0, 7.0, 180.0, 270.0)[1:])
    return points


def lid_contours():
    return [
        ("HOLES", circle_contour(18.333, 322.833, 1.5, 0.0)),
        ("CUT", outline_rect_contour(10.0, 314.5, 94.0, 94.0)),
        ("HOLES", circle_contour(95.667, 322.833, 1.5, 90.0)),
        ("HOLES", circle_contour(95.667, 400.167, 1.5, 180.0)),
        ("HOLES", circle_contour(18.333, 400.167, 1.5, -90.0)),
        ("CUT", upper_mount_contour(17.243, 410.0)),
        ("HOLES", circle_contour(33.909, 421.333, 1.0, 90.0)),
        ("CUT", lower_mount_contour(10.0, 413.0)),
        ("HOLES", circle_contour(21.333, 429.667, 1.0, -90.0)),
        ("CUT", upper_mount_contour(53.985, 410.0)),
        ("HOLES", circle_contour(70.652, 421.333, 1.0, 90.0)),
        ("CUT", lower_mount_contour(46.743, 413.0)),
        ("HOLES", circle_contour(58.076, 429.667, 1.0, -90.0)),
    ]


def upper_mount_contour(x, y):
    return [
        (x, y + 3.0),
        (x + 9.5, y + 3.0),
        (x + 9.5, y),
        (x + 15.5, y),
        (x + 15.5, y + 3.0),
        (x + 25.0, y + 3.0),
        (x + 25.0, y + 12.5),
        (x + 28.0, y + 12.5),
        (x + 28.0, y + 18.5),
        (x + 25.0, y + 18.5),
        (x + 25.0, y + 28.0),
        (x, y + 3.0),
    ]


def lower_mount_contour(x, y):
    return [
        (x + 28.0, y + 25.0),
        (x + 18.5, y + 25.0),
        (x + 18.5, y + 28.0),
        (x + 12.5, y + 28.0),
        (x + 12.5, y + 25.0),
        (x + 3.0, y + 25.0),
        (x + 3.0, y + 15.5),
        (x, y + 15.5),
        (x, y + 9.5),
        (x + 3.0, y + 9.5),
        (x + 3.0, y),
        (x + 28.0, y + 25.0),
    ]


def build_generated_panels(params):
    t = params.thickness
    outer_length = params.length + 2 * t
    outer_depth = params.depth + 2 * t
    mount_size = max(28.0, t * 8)
    margin = 6.0
    gap = 8.0
    column_width = max(outer_length, outer_depth, mount_size * 2 + gap)
    x1 = margin
    x2 = margin + column_width + gap
    y1 = margin
    y2 = y1 + params.height + gap
    y3 = y2 + params.height + gap
    y4 = y3 + outer_depth + gap

    return [
        make_panel("Wall 1", x1, y1, wall_part_contours(x1, y1, outer_length, params.height, params)),
        make_panel("Wall 2", x2, y1, wall_part_contours(x2, y1, outer_length, params.height, params)),
        make_panel("Wall 3", x1, y2, wall_part_contours(x1, y2, outer_depth, params.height, params)),
        make_panel("Wall 4", x2, y2, wall_part_contours(x2, y2, outer_depth, params.height, params)),
        make_panel("Bottom", x1, y3, bottom_contours(x1, y3, outer_length, outer_depth, params)),
        make_panel("Top", x2, y3, top_contours(x2, y3, outer_length, outer_depth)),
        make_panel("Mounts", x1, y4, mounts_contours(x1, y4, x2, mount_size, gap)),
    ]


def make_panel(title, x, y, contours):
    return Panel(title, x, y, contours_to_segments(contours))


def wall_part_contours(x, y, width, height, params):
    return [("CUT", fingered_rect_contour(x, y, width, height, params))]


def bottom_contours(x, y, width, height, params):
    contours = [("CUT", outline_rect_contour(x, y, width, height))]
    contours.extend(edge_slot_contours(x, y, width, height, params))
    contours.extend(corner_hole_contours(x, y, width, height, 7.0, 1.5))
    return contours


def top_contours(x, y, width, height):
    contours = [("CUT", outline_rect_contour(x, y, width, height))]
    contours.extend(corner_hole_contours(x, y, width, height, 8.0, 1.5))
    return contours


def mounts_contours(x1, y, x2, mount_size, gap):
    contours = []
    for x in [x1, x1 + mount_size + gap, x2, x2 + mount_size + gap]:
        contours.append(("CUT", [(x, y), (x + mount_size, y), (x, y + mount_size), (x, y)]))
        contours.append(("HOLES", circle_contour(x + mount_size * 0.38, y + mount_size * 0.38, 1.5, 0.0)))
    return contours


def fingered_rect_contour(x, y, width, height, params):
    t = params.thickness
    fw = params.finger_width
    points = [(x, y)]
    points.extend(fingered_edge_points((x, y), (x + width, y), (0, t), fw))
    points.extend(fingered_edge_points((x + width, y), (x + width, y + height), (-t, 0), fw))
    points.extend(fingered_edge_points((x + width, y + height), (x, y + height), (0, -t), fw))
    points.extend(fingered_edge_points((x, y + height), (x, y), (t, 0), fw))
    return points


def fingered_edge_points(start, end, inward, finger_width):
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < 0.0001:
        return []

    tx = dx / length
    ty = dy / length
    count = max(1, int(length // finger_width))
    cursor = (length - count * finger_width) / 2
    points = []

    if cursor > 0.0001:
        points.append((x1 + tx * cursor, y1 + ty * cursor))

    for index in range(count):
        next_cursor = cursor + finger_width
        base = (x1 + tx * cursor, y1 + ty * cursor)
        next_point = (x1 + tx * next_cursor, y1 + ty * next_cursor)
        if index % 2 == 0:
            points.extend(
                [
                    (base[0] + inward[0], base[1] + inward[1]),
                    (next_point[0] + inward[0], next_point[1] + inward[1]),
                    next_point,
                ]
            )
        else:
            points.append(next_point)
        cursor = next_cursor

    if math.hypot(points[-1][0] - x2, points[-1][1] - y2) > 0.0001:
        points.append((x2, y2))
    return points


def edge_slot_contours(x, y, width, height, params):
    t = params.thickness
    fw = params.finger_width
    inset = max(t, 3.0)
    contours = []

    for slot_x in slot_positions(x + t, x + width - t, fw):
        contours.append(("HOLES", rect_contour(slot_x - fw / 2, y + inset, fw, t)))
        contours.append(("HOLES", rect_contour(slot_x - fw / 2, y + height - inset - t, fw, t)))

    for slot_y in slot_positions(y + t, y + height - t, fw):
        contours.append(("HOLES", rect_contour(x + inset, slot_y - fw / 2, t, fw)))
        contours.append(("HOLES", rect_contour(x + width - inset - t, slot_y - fw / 2, t, fw)))

    return contours


def slot_positions(start, end, finger_width):
    length = end - start
    if length <= finger_width:
        return [start + length / 2]

    count = max(2, int(length // (finger_width * 2)))
    step = length / (count + 1)
    return [start + step * index for index in range(1, count + 1)]


def corner_hole_contours(x, y, width, height, offset, radius):
    return [
        ("HOLES", circle_contour(cx, cy, radius, 0.0))
        for cx, cy in [
            (x + offset, y + offset),
            (x + width - offset, y + offset),
            (x + width - offset, y + height - offset),
            (x + offset, y + height - offset),
        ]
    ]


def rect_contour(x, y, width, height):
    return [
        (x, y + height),
        (x + width, y + height),
        (x + width, y),
        (x, y),
        (x, y + height),
    ]


def outline_rect_contour(x, y, width, height):
    return [
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
        (x, y),
    ]


def circle_contour(cx, cy, radius, start_degrees):
    points = []
    for index in range(CIRCLE_STEPS + 1):
        angle = math.radians(start_degrees - 360.0 * index / CIRCLE_STEPS)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def arc_points(cx, cy, radius, start_degrees, end_degrees):
    points = []
    for index in range(CORNER_STEPS + 1):
        angle = math.radians(start_degrees + (end_degrees - start_degrees) * index / CORNER_STEPS)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def contours_to_segments(contours):
    segments = []
    for layer, contour in contours:
        segments.extend(contour_to_segments(contour, layer))
    return segments


def contour_to_segments(contour, layer):
    if len(contour) < 2:
        return []

    points = [clean_point(point) for point in contour]
    if points[0] != points[-1]:
        points.append(points[0])

    segments = []
    for start, end in zip(points, points[1:]):
        if math.hypot(end[0] - start[0], end[1] - start[1]) >= 0.0001:
            segments.append(Segment(start, end, layer))
    return segments


def clean_point(point):
    x, y = point
    return clean_number(x), clean_number(y)


def clean_number(value):
    rounded = round(value, 6)
    if abs(rounded) < 0.000001:
        return 0.0
    return rounded


def segment_bounds(segments):
    if not segments:
        return None

    points = []
    for segment in segments:
        points.extend([segment.start, segment.end])

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)
