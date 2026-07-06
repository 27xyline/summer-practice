import ezdxf

from box_geometry import BoxParams, build_panels, segment_bounds, verify_assembly


LAYER_COLORS = {"CUT": 7, "HOLES": 5}
LINE_STYLES = {
    "CUT": {"color": 250, "linetype": "K5LT32768", "lineweight": 18},
    "HOLES": {"color": 5, "linetype": "K5LT32769", "lineweight": 18},
}


def create_dxf_document(params):
    verify_assembly(params)
    segments = [segment for panel in build_panels(params) for segment in panel.segments]

    doc = ezdxf.new("R2018")
    doc.header["$MEASUREMENT"] = 1
    doc.header["$INSUNITS"] = 4
    doc.units = 4

    add_layers(doc)
    msp = doc.modelspace()
    for segment in segments:
        x1, y1 = segment.start
        x2, y2 = segment.end
        msp.add_line((x1, y1, 0), (x2, y2, 0), dxfattribs=line_attribs(segment.layer))

    bounds = segment_bounds(segments)
    if bounds is not None:
        min_x, min_y, max_x, max_y = bounds
        doc.header["$EXTMIN"] = (min_x, min_y, 0)
        doc.header["$EXTMAX"] = (max_x, max_y, 0)

    return doc


def add_layers(doc):
    for linetype in {style["linetype"] for style in LINE_STYLES.values()}:
        if not doc.linetypes.has_entry(linetype):
            doc.linetypes.add(linetype, pattern=[0.0], description="")

    for layer, color in LAYER_COLORS.items():
        if not doc.layers.has_entry(layer):
            doc.layers.new(name=layer, dxfattribs={"color": color})


def line_attribs(layer):
    attrs = {"layer": layer}
    attrs.update(LINE_STYLES.get(layer, {}))
    return attrs


def save_dxf_file(params, path):
    doc = create_dxf_document(params)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)


def write_example_files(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "electronics_box.dxf"
    save_dxf_file(BoxParams(), path)
    return [path]
