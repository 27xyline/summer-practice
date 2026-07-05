import math
import re
import ssl
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree


SVG_FILE = Path(__file__).parent / "assets" / "ElectronicsBox.svg"
SERVICE_URL = "https://box.laserbiz.ru/site.wsgi/ElectronicsBox"
SVG_CACHE = {}


class BoxParams:
    def __init__(
        self,
        length=100,
        depth=100,
        height=100,
        thickness=3,
        finger_width=6,
        clearance=0.0,
        sheet_width=230,
        sheet_height=460,
        svg_file=None,
    ):
        self.length = float(length)
        self.depth = float(depth)
        self.width = float(depth)
        self.height = float(height)
        self.thickness = float(thickness)
        self.finger_width = float(finger_width)
        self.clearance = float(clearance)
        self.sheet_width = float(sheet_width)
        self.sheet_height = float(sheet_height)
        self.svg_file = Path(svg_file) if svg_file else None


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


def query_fmt(value):
    return f"{value:.4f}".rstrip("0").rstrip(".")


def finger_joint_play(params):
    return 0.0


def validate_params(params):
    values = [
        ("Длина", params.length),
        ("Глубина", params.depth),
        ("Высота", params.height),
        ("Толщина материала", params.thickness),
        ("Ширина шипа", params.finger_width),
        ("Зазор шип-паз", params.clearance),
        ("Ширина листа", params.sheet_width),
        ("Высота листа", params.sheet_height),
    ]

    for name, value in values:
        if not math.isfinite(value):
            raise ValueError(f"{name} указана неправильно")

    for name, value in values[:5] + values[6:]:
        if value <= 0:
            raise ValueError(f"{name} должна быть положительным числом")

    if abs(params.clearance) > 0.0001:
        raise ValueError("Зазор шип-паз больше не используется: ширина шипа и паза должна совпадать")
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
    root = ElementTree.fromstring(load_svg_text(params))
    width, height = svg_size(root)
    panels = []

    for group in root.iter():
        if tag_name(group.tag) == "g" and group.attrib.get("id", "").startswith("p-"):
            segments = []
            title = group.attrib.get("id", "")
            for item in group:
                name = tag_name(item.tag)
                if name == "path":
                    layer = layer_by_color(item.attrib.get("stroke", ""))
                    segments.extend(path_segments(item.attrib.get("d", ""), height, layer))
                elif name == "text":
                    title = (item.text or title).strip()

            if segments:
                panels.append(Panel(title, 0, 0, segments))

    return panels


def load_svg_text(params):
    if params.svg_file:
        return params.svg_file.read_text(encoding="utf-8")

    key = (
        round(params.length, 3),
        round(params.depth, 3),
        round(params.height, 3),
        round(params.thickness, 3),
        round(params.finger_width, 3),
    )
    if key not in SVG_CACHE:
        SVG_CACHE[key] = download_svg(params)
    return SVG_CACHE[key]


def download_svg(params):
    query = {
        "FingerJoint_angle": "90.0",
        "FingerJoint_style": "rectangular",
        "FingerJoint_surroundingspaces": "2.0",
        "FingerJoint_bottom_lip": "0.0",
        "FingerJoint_edge_width": "1.0",
        "FingerJoint_extra_length": "0.0",
        "FingerJoint_finger": query_fmt(params.finger_width / params.thickness),
        "FingerJoint_play": query_fmt(finger_joint_play(params)),
        "FingerJoint_space": query_fmt(params.finger_width / params.thickness),
        "FingerJoint_width": "1.0",
        "x": query_fmt(params.length),
        "y": query_fmt(params.depth),
        "h": query_fmt(params.height),
        "outside": "1",
        "triangle": "25.0",
        "d1": "2.0",
        "d2": "3.0",
        "d3": "3.0",
        "outsidemounts": "1",
        "holedist": "7.0",
        "thickness": query_fmt(params.thickness),
        "format": "svg",
        "tabs": "0.0",
        "qr_code": "0",
        "debug": "0",
        "labels": "0",
        "reference": "0",
        "inner_corners": "corner",
        "burn": "0",
        "language": "ru",
        "render": "2",
    }
    url = f"{SERVICE_URL}?{urlencode(query)}"
    try:
        data = urlopen(url, timeout=20, context=ssl._create_unverified_context()).read()
    except Exception as error:
        raise ValueError(f"Не получилось получить ElectronicsBox.svg: {error}")

    text = data.decode("utf-8")
    if "<svg" not in text:
        raise ValueError("Сервис вернул неправильный SVG")
    return fix_rectangular_slots(text, params)


def fix_rectangular_slots(text, params):
    root = ElementTree.fromstring(text)
    target_long = params.finger_width
    target_short = params.thickness

    for item in root.iter():
        if tag_name(item.tag) != "path":
            continue
        if layer_by_color(item.attrib.get("stroke", "")) != "HOLES":
            continue

        bounds = path_raw_bounds(item.attrib.get("d", ""))
        if bounds is None:
            continue

        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        sizes = sorted([width, height])

        if abs(sizes[0] - params.thickness) > 0.25:
            continue
        if abs(sizes[1] - target_long) > 0.25:
            continue

        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        if width >= height:
            new_w = target_long
            new_h = target_short
        else:
            new_w = target_short
            new_h = target_long

        x1 = cx - new_w / 2
        x2 = cx + new_w / 2
        y1 = cy - new_h / 2
        y2 = cy + new_h / 2
        item.set("d", f"M {query_fmt(x1)} {query_fmt(y1)} H {query_fmt(x2)} V {query_fmt(y2)} H {query_fmt(x1)} V {query_fmt(y1)} Z")

    return ElementTree.tostring(root, encoding="unicode")

def check_slot_sizes(params):
    sizes = rectangular_hole_sizes(params)
    expected = sorted([round(params.finger_width, 1), round(params.thickness, 1)])
    for width, height in sizes:
        current = sorted([round(width, 1), round(height, 1)])
        if current == expected:
            return
    raise ValueError("Прямоугольные пазы не совпадают с размером шипов")


def check_joint_sizes(params, panels):
    expected = params.finger_width
    for size in joint_line_sizes(params, panels):
        if abs(size - expected) <= 0.05:
            return
    raise ValueError("Пальцевые соединения не совпадают с шириной шипа")


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
    root = ElementTree.fromstring(load_svg_text(params))
    result = []
    for item in root.iter():
        if tag_name(item.tag) != "path":
            continue
        if layer_by_color(item.attrib.get("stroke", "")) != "HOLES":
            continue
        bounds = path_raw_bounds(item.attrib.get("d", ""))
        if bounds is None:
            continue
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x
        height = max_y - min_y
        if width <= params.finger_width + 0.2 and height <= params.finger_width + 0.2:
            if width > 1 and height > 1:
                result.append((width, height))
    return result


def svg_size(root):
    view_box = root.attrib.get("viewBox", "0 0 0 0").replace(",", " ").split()
    if len(view_box) == 4:
        return float(view_box[2]), float(view_box[3])

    width = root.attrib.get("width", "0").replace("mm", "")
    height = root.attrib.get("height", "0").replace("mm", "")
    return float(width), float(height)


def tag_name(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def layer_by_color(color):
    if "0,0,255" in color:
        return "HOLES"
    return "CUT"


def path_segments(text, height, layer):
    tokens = re.findall(r"[MmLlHhVvCcZz]|[-+]?\d+(?:\.\d+)?", text)
    segments = []
    i = 0
    command = ""
    point = (0.0, 0.0)
    start = (0.0, 0.0)

    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1

        if command in ["M", "m"]:
            x = float(tokens[i])
            y = float(tokens[i + 1])
            i += 2
            if command == "m":
                x += point[0]
                y += point[1]
            point = (x, y)
            start = point
            command = "L" if command == "M" else "l"
        elif command in ["L", "l"]:
            x = float(tokens[i])
            y = float(tokens[i + 1])
            i += 2
            if command == "l":
                x += point[0]
                y += point[1]
            new_point = (x, y)
            add_line(segments, point, new_point, height, layer)
            point = new_point
        elif command in ["H", "h"]:
            x = float(tokens[i])
            i += 1
            if command == "h":
                x += point[0]
            new_point = (x, point[1])
            add_line(segments, point, new_point, height, layer)
            point = new_point
        elif command in ["V", "v"]:
            y = float(tokens[i])
            i += 1
            if command == "v":
                y += point[1]
            new_point = (point[0], y)
            add_line(segments, point, new_point, height, layer)
            point = new_point
        elif command in ["C", "c"]:
            p1 = (float(tokens[i]), float(tokens[i + 1]))
            p2 = (float(tokens[i + 2]), float(tokens[i + 3]))
            p3 = (float(tokens[i + 4]), float(tokens[i + 5]))
            i += 6
            if command == "c":
                p1 = (p1[0] + point[0], p1[1] + point[1])
                p2 = (p2[0] + point[0], p2[1] + point[1])
                p3 = (p3[0] + point[0], p3[1] + point[1])
            add_curve(segments, point, p1, p2, p3, height, layer)
            point = p3
        elif command in ["Z", "z"]:
            add_line(segments, point, start, height, layer)
            point = start
            command = ""
        else:
            i += 1

    return segments


def add_line(segments, p1, p2, height, layer):
    x1, y1 = p1
    x2, y2 = p2
    if math.hypot(x2 - x1, y2 - y1) < 0.0001:
        return
    segments.append(Segment("line", (x1, height - y1, x2, height - y2), layer))


def add_curve(segments, p0, p1, p2, p3, height, layer):
    last = p0
    for n in range(1, 17):
        t = n / 16
        x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
        y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
        current = (x, y)
        add_line(segments, last, current, height, layer)
        last = current


def path_raw_bounds(text):
    tokens = re.findall(r"[MmLlHhVvCcZz]|[-+]?\d+(?:\.\d+)?", text)
    points = []
    i = 0
    command = ""
    point = (0.0, 0.0)
    start = (0.0, 0.0)

    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1

        if command in ["M", "m", "L", "l"]:
            x = float(tokens[i])
            y = float(tokens[i + 1])
            i += 2
            if command in ["m", "l"]:
                x += point[0]
                y += point[1]
            point = (x, y)
            points.append(point)
            if command in ["M", "m"]:
                start = point
                command = "L" if command == "M" else "l"
        elif command in ["H", "h"]:
            x = float(tokens[i])
            i += 1
            if command == "h":
                x += point[0]
            point = (x, point[1])
            points.append(point)
        elif command in ["V", "v"]:
            y = float(tokens[i])
            i += 1
            if command == "v":
                y += point[1]
            point = (point[0], y)
            points.append(point)
        elif command in ["C", "c"]:
            values = [float(tokens[i + n]) for n in range(6)]
            i += 6
            curve_points = [(values[0], values[1]), (values[2], values[3]), (values[4], values[5])]
            if command == "c":
                curve_points = [(x + point[0], y + point[1]) for x, y in curve_points]
            points.extend(curve_points)
            point = curve_points[-1]
        elif command in ["Z", "z"]:
            point = start
            points.append(point)
            command = ""
        else:
            i += 1

    if not points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


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
        elif segment.kind == "arc":
            x, y, r = segment.values[:3]
            points.append((x - r, y - r))
            points.append((x + r, y + r))
        elif segment.kind == "rect":
            x, y, w, h = segment.values
            points.append((x, y))
            points.append((x + w, y + h))

    if not points:
        return None

    xs = []
    ys = []
    for x, y in points:
        xs.append(x)
        ys.append(y)

    return min(xs), min(ys), max(xs), max(ys)
