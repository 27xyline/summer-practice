import ezdxf

from box_geometry import BoxParams, build_panels, segment_bounds, verify_assembly


def add_layer(doc, name):
    colors = {"CUT": 7, "HOLES": 5}
    if not doc.layers.has_entry(name):
        doc.layers.new(name=name, dxfattribs={"color": colors.get(name, 7)})


def layer_color(layer):
    colors = {"CUT": 250, "HOLES": 5}
    return colors.get(layer, 7)


def layer_linetype(layer):
    linetypes = {"CUT": "K5LT32768", "HOLES": "K5LT32769"}
    return linetypes.get(layer, "Continuous")


def ensure_linetypes(doc):
    for name in ["K5LT32769", "K5LT32768"]:
        if not doc.linetypes.has_entry(name):
            doc.linetypes.add(name, pattern=[0.0], description="")


def ensure_reference_layers(doc):
    for name in ["Системный слой", "0 (1)"]:
        add_layer(doc, name)


def segment_attribs(segment):
    return {
        "layer": segment.layer,
        "color": layer_color(segment.layer),
        "linetype": layer_linetype(segment.layer),
        "lineweight": 18,
    }


def add_segment(doc, msp, segment):
    add_layer(doc, segment.layer)
    attribs = segment_attribs(segment)

    if segment.kind == "line":
        x1, y1, x2, y2 = segment.values
        msp.add_line((x1, y1, 0), (x2, y2, 0), dxfattribs=attribs)
    elif segment.kind == "circle":
        x, y, r = segment.values
        msp.add_circle((x, y, 0), r, dxfattribs=attribs)
    elif segment.kind == "rect":
        x, y, w, h = segment.values
        points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        msp.add_lwpolyline(points, close=True, dxfattribs=attribs)
    else:
        raise ValueError(f"Неподдерживаемый сегмент DXF: {segment.kind}")


def create_dxf_document(params):
    verify_assembly(params)

    doc = ezdxf.new("R2018")
    doc.header["$MEASUREMENT"] = 1
    doc.header["$INSUNITS"] = 4
    doc.units = 4
    ensure_linetypes(doc)
    ensure_reference_layers(doc)
    msp = doc.modelspace()

    for name in ["CUT", "HOLES"]:
        add_layer(doc, name)

    segments = []
    for panel in build_panels(params):
        for segment in panel.segments:
            segments.append(segment)
            add_segment(doc, msp, segment)

    bounds = segment_bounds(segments)
    if bounds is not None:
        min_x, min_y, max_x, max_y = bounds
        doc.header["$EXTMIN"] = (min_x, min_y, 0)
        doc.header["$EXTMAX"] = (max_x, max_y, 0)

    return doc


def save_dxf_file(params, path):
    doc = create_dxf_document(params)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def write_example_files(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "electronics_box.dxf"
    save_dxf_file(BoxParams(), path)
    return [path]
