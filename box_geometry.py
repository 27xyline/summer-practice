import math
from dataclasses import dataclass


Point = tuple[float, float]

CUT = "CUT"
HOLES = "HOLES"

EPSILON = 0.0001
ZERO_EPSILON = 0.000001

CIRCLE_STEPS = 176
CORNER_STEPS = 48


@dataclass
class BoxParams:
    length: float = 100
    depth: float = 100
    height: float = 100
    thickness: float = 3
    finger_width: float = 6
    sheet_width: float = 300
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
    layer: str = CUT

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
    segments = collect_segments(panels)
    bounds = segment_bounds(segments)
    if bounds is None:
        raise ValueError("В чертеже нет линий")

    min_x, min_y, max_x, max_y = bounds
    if min_x < -0.001 or min_y < -0.001:
        raise ValueError("Чертеж выходит в отрицательные координаты")

    layout_width = max_x - min_x
    layout_height = max_y - min_y

    if layout_width > params.sheet_width + 0.001:
        raise ValueError(f"Раскладка шире листа: {fmt(layout_width)} мм > {fmt(params.sheet_width)} мм")
    if layout_height > params.sheet_height + 0.001:
        raise ValueError(f"Раскладка выше листа: {fmt(layout_height)} мм > {fmt(params.sheet_height)} мм")


def build_panels(params):
    validate_params(params)
    return build_generated_panels(params)


def collect_segments(panels):
    segments = []
    for panel in panels:
        segments.extend(panel.segments)
    return segments


# Единый параметрический генератор.
def build_generated_panels(params):
    contours = []

    for x, y, width, style in wall_layout(params):
        contours.extend(wall_contours(x, y, width, params.height, params, style))

    bottom_x, bottom_y, bottom_width, bottom_height = bottom_layout(params)
    contours.extend(bottom_contours(bottom_x, bottom_y, bottom_width, bottom_height, params))

    top_x, top_y, top_width, top_height = top_layout(params)
    contours.extend(top_contours(top_x, top_y, top_width, top_height, params))

    mounts_x, mounts_y = mounts_layout(params)
    contours.extend(mounts_contours(mounts_x, mounts_y, params))

    return [make_panel("ElectronicsBox", 0, 0, contours)]


def make_panel(title, x, y, contours):
    segments = contours_to_segments(contours)
    return Panel(title, x, y, segments)


def layout_margin():
    return 10.0


def layout_gap(params):
    return params.thickness / 2


def wall_layout(params):
    margin = layout_margin()
    gap = layout_gap(params)
    x1 = margin
    x2 = margin + params.length + gap
    y1 = margin
    y2 = margin + params.height + gap

    return [
        (x1, y1, params.length, "outer"),
        (x2, y1, params.depth, "inner"),
        (x2, y2, params.depth, "inner"),
        (x1, y2, params.length, "outer"),
    ]


def bottom_layout(params):
    margin = layout_margin()
    gap = layout_gap(params)
    y = margin + params.height * 2 + gap * 2
    return margin, y, bottom_plate_width(params), params.depth


def top_layout(params):
    bottom_x, bottom_y, _, bottom_height = bottom_layout(params)
    y = bottom_y + bottom_height + layout_gap(params)
    width = max(params.length - 2 * params.thickness, params.thickness)
    height = max(params.depth - 2 * params.thickness, params.thickness)
    return bottom_x, y, width, height


def mounts_layout(params):
    top_x, top_y, top_width, _ = top_layout(params)
    return top_x + top_width + layout_gap(params), top_y


def wall_contours(x, y, width, height, params, style):
    slot_offset = wall_mount_slot_offset(params)
    slot_y = y + height - slot_offset - params.thickness
    return [
        (
            HOLES,
            rect_contour(
                x + slot_offset,
                slot_y,
                params.finger_width,
                params.thickness,
            ),
        ),
        (
            HOLES,
            rect_contour(
                x + width - slot_offset - params.finger_width,
                slot_y,
                params.finger_width,
                params.thickness,
            ),
        ),
        (CUT, wall_outline(x, y, width, height, params, style)),
    ]


def wall_outline(x, y, width, height, params, style):
    thickness = params.thickness
    top_start = top_finger_start(width, params)
    points = [(x + thickness, y + thickness), (x + top_start, y + thickness)]
    add_wall_top_fingers(points, x, y, width, params)

    if style == "outer":
        points.append((x + width, y + thickness))
        points.extend(wall_side_down(x + width, x + width - thickness, y, height, params))
        points.extend([(x + thickness, y + height), (x, y + height)])
        points.extend(wall_side_up(x, x + thickness, y, height, params))
    else:
        points.extend(wall_side_down(x + width - thickness, x + width, y, height, params))
        points.append((x + thickness, y + height))
        points.extend(wall_side_up(x + thickness, x, y, height, params))

    return points


def add_wall_top_fingers(points, x, y, width, params):
    thickness = params.thickness
    finger_width = params.finger_width
    start = top_finger_start(width, params)

    for index in range(joint_count(width, params)):
        current_x = start + index * finger_width * 2
        points.extend(
            [
                (x + current_x, y),
                (x + current_x + finger_width, y),
                (x + current_x + finger_width, y + thickness),
                (x + current_x + finger_width * 2, y + thickness),
            ]
        )

    points[-1] = (x + width - thickness, y + thickness)


def wall_side_down(edge_x, notch_x, y, height, params):
    points = []
    for offset in side_finger_offsets(height, params):
        points.extend(
            [
                (edge_x, y + offset),
                (notch_x, y + offset),
                (notch_x, y + offset + params.finger_width),
                (edge_x, y + offset + params.finger_width),
            ]
        )

    points.append((edge_x, y + height))
    if edge_x > notch_x and abs(edge_x - notch_x) == params.thickness:
        points.append((notch_x, y + height))

    return points


def wall_side_up(edge_x, notch_x, y, height, params):
    points = []
    offsets = side_finger_offsets(height, params)

    for offset in reversed(offsets):
        upper_offset = offset + params.finger_width
        points.extend(
            [
                (edge_x, y + upper_offset),
                (notch_x, y + upper_offset),
                (notch_x, y + offset),
                (edge_x, y + offset),
            ]
        )

    if edge_x < notch_x:
        points.extend([(edge_x, y + params.thickness), (notch_x, y + params.thickness)])
    else:
        points.append((edge_x, y + params.thickness))

    return points


def joint_count(length, params):
    available = max(0.0, length - 2 * params.thickness)
    return max(1, int(available // (params.finger_width * 2)))


def top_finger_start(length, params):
    available = max(0.0, length - 2 * params.thickness)
    used = joint_count(length, params) * params.finger_width * 2
    return params.thickness + (available - used) / 2 + params.thickness


def side_finger_offsets(length, params):
    start = top_finger_start(length, params) + params.thickness / 2
    return [start + index * params.finger_width * 2 for index in range(joint_count(length, params))]


def bottom_contours(x, y, width, height, params):
    radius = bottom_corner_radius(params)
    contours = [
        (HOLES, circle_contour(x + radius, y + radius, params.thickness / 2, 0.0)),
        (CUT, rounded_bottom_outline(x, y, width, height, params)),
        (HOLES, circle_contour(x + width - radius, y + radius, params.thickness / 2, 90.0)),
    ]

    side = bottom_side_extension(params)
    for slot_y in bottom_slot_ys(y, height, params):
        contours.append(
            (
                HOLES,
                rect_contour(
                    x + width - side - params.thickness,
                    slot_y,
                    params.thickness,
                    params.finger_width,
                ),
            )
        )

    contours.append(
        (HOLES, circle_contour(x + width - radius, y + height - radius, params.thickness / 2, 180.0))
    )
    contours.append((HOLES, circle_contour(x + radius, y + height - radius, params.thickness / 2, -90.0)))

    for slot_y in reversed(bottom_slot_ys(y, height, params)):
        contours.append((HOLES, rect_contour(x + side, slot_y, params.thickness, params.finger_width)))

    return contours


def rounded_bottom_outline(x, y, width, height, params):
    thickness = params.thickness
    finger_width = params.finger_width
    radius = bottom_corner_radius(params)
    side = bottom_side_extension(params)
    start = top_finger_start(params.length, params)
    count = joint_count(params.length, params)

    points = [(x + radius, y), (x + side + thickness, y), (x + side + start, y)]

    for index in range(count):
        current_x = x + side + start + index * finger_width * 2
        points.extend(
            [
                (current_x, y + thickness),
                (current_x + finger_width, y + thickness),
                (current_x + finger_width, y),
                (current_x + finger_width * 2, y),
            ]
        )

    points[-1] = (x + width - side - thickness, y)
    points.append((x + width - radius, y))
    points.extend(arc_points(x + width - radius, y + radius, radius, -90.0, 0.0)[1:])
    points.append((x + width, y + height - radius))
    points.extend(arc_points(x + width - radius, y + height - radius, radius, 0.0, 90.0)[1:])
    points.extend([(x + width - side - thickness, y + height), (x + width - side - start, y + height)])

    for index in range(count):
        current_x = x + width - side - start - index * finger_width * 2
        points.extend(
            [
                (current_x, y + height - thickness),
                (current_x - finger_width, y + height - thickness),
                (current_x - finger_width, y + height),
                (current_x - finger_width * 2, y + height),
            ]
        )

    points[-1] = (x + side + thickness, y + height)
    points.append((x + radius, y + height))
    points.extend(arc_points(x + radius, y + height - radius, radius, 90.0, 180.0)[1:])
    points.append((x, y + radius))
    points.extend(arc_points(x + radius, y + radius, radius, 180.0, 270.0)[1:])
    return points


def bottom_plate_width(params):
    return params.length + 2 * bottom_side_extension(params)


def bottom_side_extension(params):
    return max(14.0, params.thickness * 4 + 2)


def bottom_corner_radius(params):
    return max(7.0, params.thickness * 2 + 1)


def bottom_slot_ys(y, height, params):
    start = top_finger_start(height, params)
    return [y + start + index * params.finger_width * 2 for index in range(joint_count(height, params))]


def top_contours(x, y, width, height, params):
    offset = min(params.finger_width + params.thickness * 0.75, width / 2, height / 2)
    radius = params.thickness / 2
    return [
        (HOLES, circle_contour(round(x + offset, 3), round(y + offset, 3), radius, 0.0)),
        (CUT, outline_rect_contour(x, y, width, height)),
        (HOLES, circle_contour(round(x + width - offset, 3), round(y + offset, 3), radius, 90.0)),
        (HOLES, circle_contour(round(x + width - offset, 3), round(y + height - offset, 3), radius, 180.0)),
        (HOLES, circle_contour(round(x + offset, 3), round(y + height - offset, 3), radius, -90.0)),
    ]


def mounts_contours(x, y, params):
    size = mount_size(params)
    radius = max(1.0, params.thickness / 3)
    gap = params.thickness
    second_pair_y = y + size + params.thickness + gap

    upper_x = x + size / 4
    lower_x = x

    upper_y_1 = y
    lower_y_1 = y + params.thickness
    upper_y_2 = second_pair_y
    lower_y_2 = second_pair_y + params.thickness

    return [
        (CUT, upper_mount_contour(upper_x, upper_y_1, size, params)),
        (HOLES, circle_contour(upper_x + size * 0.6, upper_y_1 + size * 0.4, radius, 90.0)),
        (CUT, lower_mount_contour(lower_x, lower_y_1, size, params)),
        (HOLES, circle_contour(lower_x + size * 0.4, lower_y_1 + size * 0.6, radius, -90.0)),
        (CUT, upper_mount_contour(upper_x, upper_y_2, size, params)),
        (HOLES, circle_contour(upper_x + size * 0.6, upper_y_2 + size * 0.4, radius, 90.0)),
        (CUT, lower_mount_contour(lower_x, lower_y_2, size, params)),
        (HOLES, circle_contour(lower_x + size * 0.4, lower_y_2 + size * 0.6, radius, -90.0)),
    ]


def mount_size(params):
    nominal_size = 28.0
    scale = min(params.length, params.depth, params.height) / 100.0
    minimum_size = params.finger_width + params.thickness * 2
    return max(minimum_size, nominal_size * scale)


def wall_mount_slot_offset(params):
    return mount_notch_center(mount_size(params), params)


def mount_notch_center(size, params):
    return size / 2 - params.thickness / 2


def upper_mount_contour(x, y, size, params):
    thickness = params.thickness
    finger_width = params.finger_width
    notch_center = mount_notch_center(size, params)
    notch_start = notch_center - finger_width / 2
    notch_end = notch_center + finger_width / 2
    inner_edge = size - thickness

    return [
        (x, y + thickness),
        (x + notch_start, y + thickness),
        (x + notch_start, y),
        (x + notch_end, y),
        (x + notch_end, y + thickness),
        (x + inner_edge, y + thickness),
        (x + inner_edge, y + notch_center),
        (x + size, y + notch_center),
        (x + size, y + notch_center + finger_width),
        (x + inner_edge, y + notch_center + finger_width),
        (x + inner_edge, y + size),
        (x, y + thickness),
    ]


def lower_mount_contour(x, y, size, params):
    thickness = params.thickness
    finger_width = params.finger_width
    notch_center = mount_notch_center(size, params)
    notch_start = notch_center - finger_width / 2
    notch_end = notch_center + finger_width / 2
    inner_edge = size - thickness

    return [
        (x + size, y + inner_edge),
        (x + notch_center + finger_width, y + inner_edge),
        (x + notch_center + finger_width, y + size),
        (x + notch_center, y + size),
        (x + notch_center, y + inner_edge),
        (x + thickness, y + inner_edge),
        (x + thickness, y + notch_end),
        (x, y + notch_end),
        (x, y + notch_start),
        (x + thickness, y + notch_start),
        (x + thickness, y),
        (x + size, y + inner_edge),
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

    points = []
    for point in contour:
        points.append(clean_point(point))

    if points[0] != points[-1]:
        points.append(points[0])

    segments = []
    for start, end in zip(points, points[1:]):
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        if length >= EPSILON:
            segments.append(Segment(start, end, layer))

    return segments


def clean_point(point):
    x, y = point
    return clean_number(x), clean_number(y)


def clean_number(value):
    rounded = round(value, 6)
    if abs(rounded) < ZERO_EPSILON:
        return 0.0
    return rounded


def segment_bounds(segments):
    if not segments:
        return None

    min_x = min_y = math.inf
    max_x = max_y = -math.inf

    for segment in segments:
        for x, y in [segment.start, segment.end]:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    return min_x, min_y, max_x, max_y
