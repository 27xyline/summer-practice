import math
import re
from pathlib import Path
from xml.etree import ElementTree


SVG_FILE = Path(__file__).parent / "assets" / "ElectronicsBox.svg"


class BoxParams:
    def __init__(self, svg_file=SVG_FILE, label="ElectronicsBox"):
        self.svg_file = Path(svg_file)
        self.label = label


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
    return f"{value:.4f}".rstrip("0").rstrip(".")


def validate_params(params):
    if not params.svg_file.exists():
        raise ValueError("Не найден файл образца SVG")


def verify_assembly(params):
    validate_params(params)
    panels = build_panels(params)
    segments = []
    for panel in panels:
        segments.extend(panel.segments)

    bounds = segment_bounds(segments)
    if bounds is None:
        raise ValueError("В образце нет линий")

    min_x, min_y, max_x, max_y = bounds
    if min_x < 0 or min_y < 0:
        raise ValueError("Чертеж выходит в отрицательные координаты")
    if max_x - min_x > 230 or max_y - min_y > 460:
        raise ValueError("Чертеж больше ожидаемого листа")


def build_panels(params):
    validate_params(params)
    root = ElementTree.parse(params.svg_file).getroot()
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
                    segments.append(text_segment(item, height))

            panels.append(Panel(title, 0, 0, segments))

    if not panels:
        segments = []
        for item in root.iter():
            if tag_name(item.tag) == "path":
                layer = layer_by_color(item.attrib.get("stroke", ""))
                segments.extend(path_segments(item.attrib.get("d", ""), height, layer))
        panels.append(Panel(params.label, 0, 0, segments))

    return panels


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
    if "255,0,0" in color:
        return "TEXT"
    return "CUT"


def text_segment(item, height):
    x = 0
    y = 0
    transform = item.attrib.get("transform", "")
    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", transform)
    if len(numbers) >= 6:
        x = float(numbers[4])
        y = float(numbers[5])
    else:
        x = float(item.attrib.get("x", 0))
        y = float(item.attrib.get("y", 0))

    size_text = item.attrib.get("font-size", "4").replace("px", "")
    size = float(size_text)
    return Segment("text", (x, height - y, item.text or "", size), "TEXT")


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
        elif segment.kind == "text":
            x, y, text, size = segment.values
            points.append((x, y))
            points.append((x + len(text) * size * 0.6, y + size))

    if not points:
        return None

    xs = []
    ys = []
    for x, y in points:
        xs.append(x)
        ys.append(y)

    return min(xs), min(ys), max(xs), max(ys)
