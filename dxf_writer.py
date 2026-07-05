import ezdxf

from box_geometry import BoxParams, build_panels, validate_params, verify_assembly


def add_layer(doc, name):
    colors = {"CUT": 250, "HOLES": 5, "TEXT": 1}
    if not doc.layers.has_entry(name):
        doc.layers.new(name=name, dxfattribs={"color": colors.get(name, 7)})


def layer_color(layer):
    colors = {"CUT": 250, "HOLES": 5, "TEXT": 1}
    return colors.get(layer, 7)


def add_segment(doc, msp, segment):
    add_layer(doc, segment.layer)
    color = layer_color(segment.layer)

    if segment.kind == "line":
        x1, y1, x2, y2 = segment.values
        msp.add_line((x1, y1, 0), (x2, y2, 0), dxfattribs={"layer": segment.layer, "color": color})
    elif segment.kind == "circle":
        x, y, r = segment.values
        msp.add_circle((x, y, 0), r, dxfattribs={"layer": segment.layer, "color": color})
    elif segment.kind == "arc":
        x, y, r, a1, a2 = segment.values
        msp.add_arc((x, y, 0), r, a1, a2, dxfattribs={"layer": segment.layer, "color": color})
    elif segment.kind == "text":
        x, y, text, size = segment.values
        item = msp.add_text(text, dxfattribs={"height": size, "layer": segment.layer, "color": color})
        item.dxf.insert = (x, y, 0)


def create_dxf_document(params):
    validate_params(params)
    verify_assembly(params)

    doc = ezdxf.new("R2010")
    doc.header["$MEASUREMENT"] = 1
    doc.header["$INSUNITS"] = 4
    doc.units = 4
    msp = doc.modelspace()

    for name in ["CUT", "HOLES", "TEXT"]:
        add_layer(doc, name)

    for panel in build_panels(params):
        for segment in panel.segments:
            add_segment(doc, msp, segment)

    return doc


def save_dxf_file(params, path):
    doc = create_dxf_document(params)
    doc.saveas(path)


def write_example_files(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "electronics_box.dxf"
    save_dxf_file(BoxParams(), path)
    return [path]
