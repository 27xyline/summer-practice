import math


SLOT_TOLERANCE = 0.05
JOINT_TOLERANCE = 0.05
STANDARD_PARAMS = (100.0, 100.0, 100.0, 3.0, 6.0)
CIRCLE_SEGMENTS = 176
CORNER_SEGMENTS = 48


class BoxParams:
    def __init__(
        self,
        length=100,
        depth=100,
        height=100,
        thickness=3,
        finger_width=6,
        sheet_width=230,
        sheet_height=460,
    ):
        self.length = float(length)
        self.depth = float(depth)
        self.height = float(height)
        self.thickness = float(thickness)
        self.finger_width = float(finger_width)
        self.sheet_width = float(sheet_width)
        self.sheet_height = float(sheet_height)


class Segment:
    def __init__(self, kind, values, layer="CUT"):
        self.kind = kind
        self.values = values
        self.layer = layer


class Panel:
    def __init__(self, title, x, y, segments):
        self.title = title
        self.x = x
        self.y = y
        self.segments = segments


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
    segments = []
    for panel in panels:
        segments.extend(panel.segments)

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

    check_joint_sizes(params, panels)
    check_slot_sizes(params)


def build_panels(params):
    validate_params(params)
    if uses_standard_geometry(params):
        return build_standard_electronics_box(params)
    return build_generated_panels(params)


def uses_standard_geometry(params):
    values = (
        params.length,
        params.depth,
        params.height,
        params.thickness,
        params.finger_width,
    )
    return all(abs(value - expected) < 0.0001 for value, expected in zip(values, STANDARD_PARAMS))


def build_standard_electronics_box(params):
    segments = []

    for x, y, style in [
        (10.0, 10.0, "outer"),
        (111.5, 10.0, "inner"),
        (111.5, 111.5, "inner"),
        (10.0, 111.5, "outer"),
    ]:
        add_wall_mount_slots(segments, x, y)
        add_wall_outline(segments, x, y, style)

    add_round_base_holes_and_outline(segments)
    add_lid_and_mounts(segments)
    return [Panel("ElectronicsBox", 0, 0, segments)]


def add_wall_mount_slots(segments, x, y):
    for slot_x in [x + 12.5, x + 81.5]:
        add_rect_lines(segments, slot_x, y + 94.0, 6.0, 3.0, "HOLES")


def add_wall_outline(segments, x, y, style):
    points = []
    t = 3.0
    w = 100.0
    h = 100.0

    points.append((x + t, y + t))
    points.append((x + 11.0, y + t))
    for current_x in range(11, 84, 12):
        points.append((x + current_x, y))
        points.append((x + current_x + 6.0, y))
        points.append((x + current_x + 6.0, y + t))
        points.append((x + current_x + 12.0, y + t))

    if style == "outer":
        points[-1] = (x + w - t, y + t)
        points.append((x + w, y + t))
        add_outer_right_edge(points, x, y, w, h, t)
        points.append((x + t, y + h))
        points.append((x, y + h))
        add_outer_left_edge(points, x, y, h, t)
    else:
        points[-1] = (x + w - t, y + t)
        add_inner_right_edge(points, x, y, w, h, t)
        points.append((x + t, y + h))
        add_inner_left_edge(points, x, y, h, t)

    add_polyline_lines(segments, points, "CUT")


def add_outer_right_edge(points, x, y, w, h, t):
    for offset in [12.5, 24.5, 36.5, 48.5, 60.5, 72.5, 84.5]:
        points.append((x + w, y + offset))
        points.append((x + w - t, y + offset))
        points.append((x + w - t, y + offset + 6.0))
        points.append((x + w, y + offset + 6.0))
    points.append((x + w, y + h))
    points.append((x + w - t, y + h))


def add_outer_left_edge(points, x, y, h, t):
    for offset in [90.5, 78.5, 66.5, 54.5, 42.5, 30.5, 18.5]:
        points.append((x, y + offset))
        points.append((x + t, y + offset))
        points.append((x + t, y + offset - 6.0))
        points.append((x, y + offset - 6.0))
    points.append((x, y + t))
    points.append((x + t, y + t))


def add_inner_right_edge(points, x, y, w, h, t):
    for offset in [12.5, 24.5, 36.5, 48.5, 60.5, 72.5, 84.5]:
        points.append((x + w - t, y + offset))
        points.append((x + w, y + offset))
        points.append((x + w, y + offset + 6.0))
        points.append((x + w - t, y + offset + 6.0))
    points.append((x + w - t, y + h))


def add_inner_left_edge(points, x, y, h, t):
    for offset in [90.5, 78.5, 66.5, 54.5, 42.5, 30.5, 18.5]:
        points.append((x + t, y + offset))
        points.append((x, y + offset))
        points.append((x, y + offset - 6.0))
        points.append((x + t, y + offset - 6.0))
    points.append((x + t, y + t))


def add_round_base_holes_and_outline(segments):
    add_circle_lines(segments, 17.0, 220.0, 1.5, 0.0)
    add_rounded_base_outline(segments)
    add_circle_lines(segments, 131.0, 220.0, 1.5, 90.0)

    for slot_y in [224.0, 236.0, 248.0, 260.0, 272.0, 284.0, 296.0]:
        add_rect_lines(segments, 121.0, slot_y, 3.0, 6.0, "HOLES")

    add_circle_lines(segments, 131.0, 306.0, 1.5, 180.0)
    add_circle_lines(segments, 17.0, 306.0, 1.5, -90.0)

    for slot_y in [296.0, 284.0, 272.0, 260.0, 248.0, 236.0, 224.0]:
        add_rect_lines(segments, 24.0, slot_y, 3.0, 6.0, "HOLES")


def add_rounded_base_outline(segments):
    points = [(17.0, 213.0), (27.0, 213.0), (35.0, 213.0)]
    for current_x in range(35, 108, 12):
        points.append((current_x, 216.0))
        points.append((current_x + 6.0, 216.0))
        points.append((current_x + 6.0, 213.0))
        points.append((current_x + 12.0, 213.0))
    points[-1] = (121.0, 213.0)
    points.append((131.0, 213.0))
    points.extend(arc_points(131.0, 220.0, 7.0, -90.0, 0.0)[1:])
    points.append((138.0, 306.0))
    points.extend(arc_points(131.0, 306.0, 7.0, 0.0, 90.0)[1:])
    points.extend([(121.0, 313.0), (113.0, 313.0)])
    for current_x in range(113, 34, -12):
        points.append((current_x, 310.0))
        points.append((current_x - 6.0, 310.0))
        points.append((current_x - 6.0, 313.0))
        points.append((current_x - 12.0, 313.0))
    points[-1] = (27.0, 313.0)
    points.append((17.0, 313.0))
    points.extend(arc_points(17.0, 306.0, 7.0, 90.0, 180.0)[1:])
    points.append((10.0, 220.0))
    points.extend(arc_points(17.0, 220.0, 7.0, 180.0, 270.0)[1:])
    add_polyline_lines(segments, points, "CUT")


def add_lid_and_mounts(segments):
    add_circle_lines(segments, 18.333, 322.833, 1.5, 0.0)
    add_polyline_lines(
        segments,
        [(10.0, 314.5), (104.0, 314.5), (104.0, 408.5), (10.0, 408.5), (10.0, 314.5)],
        "CUT",
    )
    add_circle_lines(segments, 95.667, 322.833, 1.5, 90.0)
    add_circle_lines(segments, 95.667, 400.167, 1.5, 180.0)
    add_circle_lines(segments, 18.333, 400.167, 1.5, -90.0)

    add_upper_mount(segments, 17.243, 410.0)
    add_circle_lines(segments, 33.909, 421.333, 1.0, 90.0)
    add_lower_mount(segments, 10.0, 413.0)
    add_circle_lines(segments, 21.333, 429.667, 1.0, -90.0)
    add_upper_mount(segments, 53.985, 410.0)
    add_circle_lines(segments, 70.652, 421.333, 1.0, 90.0)
    add_lower_mount(segments, 46.743, 413.0)
    add_circle_lines(segments, 58.076, 429.667, 1.0, -90.0)


def add_upper_mount(segments, x, y):
    add_polyline_lines(
        segments,
        [
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
        ],
        "CUT",
    )


def add_lower_mount(segments, x, y):
    add_polyline_lines(
        segments,
        [
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
        ],
        "CUT",
    )


def add_rect_lines(segments, x, y, width, height, layer):
    add_polyline_lines(
        segments,
        [
            (x, y + height),
            (x + width, y + height),
            (x + width, y),
            (x, y),
            (x, y + height),
        ],
        layer,
    )


def add_circle_lines(segments, cx, cy, radius, start_degrees):
    points = []
    for index in range(CIRCLE_SEGMENTS + 1):
        angle = math.radians(start_degrees - 360.0 * index / CIRCLE_SEGMENTS)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    add_polyline_lines(segments, points, "HOLES")


def arc_points(cx, cy, radius, start_degrees, end_degrees):
    points = []
    for index in range(CORNER_SEGMENTS + 1):
        angle = math.radians(start_degrees + (end_degrees - start_degrees) * index / CORNER_SEGMENTS)
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def add_polyline_lines(segments, points, layer):
    for index in range(len(points) - 1):
        x1, y1 = clean_point(points[index])
        x2, y2 = clean_point(points[index + 1])
        if math.hypot(x2 - x1, y2 - y1) >= 0.0001:
            segments.append(Segment("line", (x1, y1, x2, y2), layer))


def clean_point(point):
    x, y = point
    return clean_number(x), clean_number(y)


def clean_number(value):
    rounded = round(value, 6)
    if abs(rounded) < 0.000001:
        return 0.0
    return rounded


def build_generated_panels(params):
    t = params.thickness
    outer_length = params.length + 2 * t
    outer_depth = params.depth + 2 * t
    wall_height = params.height
    margin = 6.0
    gap = 8.0
    mount_size = max(28.0, t * 8)
    column_width = max(outer_length, outer_depth, mount_size * 2 + gap)
    x1 = margin
    x2 = margin + column_width + gap
    y1 = margin
    y2 = y1 + wall_height + gap
    y3 = y2 + wall_height + gap
    y4 = y3 + outer_depth + gap

    panels = [
        create_wall_panel("Wall 1", x1, y1, outer_length, wall_height, params),
        create_wall_panel("Wall 2", x2, y1, outer_length, wall_height, params),
        create_wall_panel("Wall 3", x1, y2, outer_depth, wall_height, params),
        create_wall_panel("Wall 4", x2, y2, outer_depth, wall_height, params),
        create_bottom_panel("Bottom", x1, y3, outer_length, outer_depth, params),
        create_top_panel("Top", x2, y3, outer_length, outer_depth, params),
        create_mounts_panel("Mounts", x1, y4, x2, mount_size, gap),
    ]
    return panels


def create_wall_panel(title, x, y, width, height, params):
    segments = fingered_rect_segments(x, y, width, height, params)
    return Panel(title, x, y, segments)


def create_bottom_panel(title, x, y, width, height, params):
    segments = rectangle_segments(x, y, width, height, "CUT")
    add_edge_slots(segments, x, y, width, height, params)
    add_corner_holes(segments, x, y, width, height, 7.0, 1.5)
    return Panel(title, x, y, segments)


def create_top_panel(title, x, y, width, height, params):
    segments = rectangle_segments(x, y, width, height, "CUT")
    add_corner_holes(segments, x, y, width, height, 8.0, 1.5)
    return Panel(title, x, y, segments)


def create_mounts_panel(title, x1, y, x2, mount_size, gap):
    segments = []
    positions = [
        (x1, y),
        (x1 + mount_size + gap, y),
        (x2, y),
        (x2 + mount_size + gap, y),
    ]
    for x, current_y in positions:
        add_mount(segments, x, current_y, mount_size)
    return Panel(title, x1, y, segments)


def rectangle_segments(x, y, width, height, layer):
    return [
        Segment("line", (x, y, x + width, y), layer),
        Segment("line", (x + width, y, x + width, y + height), layer),
        Segment("line", (x + width, y + height, x, y + height), layer),
        Segment("line", (x, y + height, x, y), layer),
    ]


def fingered_rect_segments(x, y, width, height, params):
    t = params.thickness
    fw = params.finger_width
    points = [(x, y)]
    points.extend(fingered_edge_points((x, y), (x + width, y), (0, t), fw))
    points.extend(fingered_edge_points((x + width, y), (x + width, y + height), (-t, 0), fw))
    points.extend(fingered_edge_points((x + width, y + height), (x, y + height), (0, -t), fw))
    points.extend(fingered_edge_points((x, y + height), (x, y), (t, 0), fw))
    return polyline_segments(points, "CUT")


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
    remainder = length - count * finger_width
    cursor = remainder / 2
    points = []

    if cursor > 0.0001:
        points.append((x1 + tx * cursor, y1 + ty * cursor))

    for index in range(count):
        base_x = x1 + tx * cursor
        base_y = y1 + ty * cursor
        next_cursor = cursor + finger_width
        next_x = x1 + tx * next_cursor
        next_y = y1 + ty * next_cursor
        if index % 2 == 0:
            points.append((base_x + inward[0], base_y + inward[1]))
            points.append((next_x + inward[0], next_y + inward[1]))
            points.append((next_x, next_y))
        else:
            points.append((next_x, next_y))
        cursor = next_cursor

    if math.hypot(points[-1][0] - x2, points[-1][1] - y2) > 0.0001:
        points.append((x2, y2))
    return points


def polyline_segments(points, layer):
    segments = []
    for index in range(len(points)):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % len(points)]
        if math.hypot(x2 - x1, y2 - y1) >= 0.0001:
            segments.append(Segment("line", (x1, y1, x2, y2), layer))
    return segments


def add_edge_slots(segments, x, y, width, height, params):
    t = params.thickness
    fw = params.finger_width
    inset = max(t, 3.0)

    for slot_x in slot_positions(x + t, x + width - t, fw):
        segments.append(Segment("rect", (slot_x - fw / 2, y + inset, fw, t), "HOLES"))
        segments.append(Segment("rect", (slot_x - fw / 2, y + height - inset - t, fw, t), "HOLES"))

    for slot_y in slot_positions(y + t, y + height - t, fw):
        segments.append(Segment("rect", (x + inset, slot_y - fw / 2, t, fw), "HOLES"))
        segments.append(Segment("rect", (x + width - inset - t, slot_y - fw / 2, t, fw), "HOLES"))


def slot_positions(start, end, finger_width):
    length = end - start
    if length <= finger_width:
        return [start + length / 2]
    count = max(2, int(length // (finger_width * 2)))
    step = length / (count + 1)
    return [start + step * index for index in range(1, count + 1)]


def add_corner_holes(segments, x, y, width, height, offset, radius):
    for cx, cy in [
        (x + offset, y + offset),
        (x + width - offset, y + offset),
        (x + width - offset, y + height - offset),
        (x + offset, y + height - offset),
    ]:
        segments.append(Segment("circle", (cx, cy, radius), "HOLES"))


def add_mount(segments, x, y, size):
    segments.extend(
        [
            Segment("line", (x, y, x + size, y), "CUT"),
            Segment("line", (x + size, y, x, y + size), "CUT"),
            Segment("line", (x, y + size, x, y), "CUT"),
            Segment("circle", (x + size * 0.38, y + size * 0.38, 1.5), "HOLES"),
        ]
    )


def check_slot_sizes(params):
    sizes = rectangular_hole_sizes(params)
    if len(sizes) < 4:
        raise ValueError("Прямоугольные пазы не найдены")

    wrong = []
    expected = sorted([params.finger_width, params.thickness])
    for width, height in sizes:
        current = sorted([width, height])
        if abs(current[0] - expected[0]) > SLOT_TOLERANCE or abs(current[1] - expected[1]) > SLOT_TOLERANCE:
            wrong.append((width, height))

    if wrong:
        sample = ", ".join(f"{fmt(width)}x{fmt(height)}" for width, height in wrong[:5])
        raise ValueError(f"Прямоугольные пазы не совпадают с размером шипов: {sample}")


def check_joint_sizes(params, panels):
    sizes = joint_line_sizes(params, panels)
    if len(sizes) < 10:
        raise ValueError("Пальцевые соединения не найдены")

    wrong = [size for size in sizes if abs(size - params.finger_width) > JOINT_TOLERANCE]
    if wrong:
        sample = ", ".join(fmt(size) for size in wrong[:5])
        raise ValueError(f"Пальцевые соединения не совпадают с шириной шипа: {sample}")


def joint_line_sizes(params, panels=None):
    if panels is None:
        panels = build_panels(params)

    sizes = []
    min_size = max(0, params.finger_width - 0.2)
    max_size = params.finger_width + 0.2

    for panel in panels:
        for segment in panel.segments:
            if segment.layer != "CUT" or segment.kind != "line":
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
    result = []
    hole_lines = []
    for panel in build_panels(params):
        for segment in panel.segments:
            if segment.layer == "HOLES" and segment.kind == "rect":
                _, _, width, height = segment.values
                result.append((width, height))
            elif segment.layer == "HOLES" and segment.kind == "line":
                hole_lines.append(segment)
    result.extend(rectangular_line_hole_sizes(hole_lines))
    return result


def rectangular_line_hole_sizes(segments):
    components = line_components(segments)
    result = []
    for component in components:
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
            result.append((width, height))

    return result


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


def segment_bounds(segments):
    points = []
    for segment in segments:
        if segment.kind == "line":
            x1, y1, x2, y2 = segment.values
            points.append((x1, y1))
            points.append((x2, y2))
        elif segment.kind == "circle":
            x, y, r = segment.values
            points.append((x - r, y - r))
            points.append((x + r, y + r))
        elif segment.kind == "rect":
            x, y, w, h = segment.values
            points.append((x, y))
            points.append((x + w, y + h))
        else:
            raise ValueError(f"Неподдерживаемый сегмент: {segment.kind}")

    if not points:
        return None

    xs = []
    ys = []
    for x, y in points:
        xs.append(x)
        ys.append(y)

    return min(xs), min(ys), max(xs), max(ys)
