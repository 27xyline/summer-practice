import ezdxf

from box_geometry import BoxParams, build_panels, fmt, validate_params, verify_assembly


def add_layer(document, layer):
    if not document.layers.has_entry(layer):
        document.layers.new(name=layer, dxfattribs={"color": 1})


def add_segment(document, modelspace, segment):
    add_layer(document, segment.layer)

    if segment.kind == "line":
        x1, y1, x2, y2 = segment.values
        modelspace.add_line((x1, y1, 0), (x2, y2, 0), dxfattribs={"layer": segment.layer})
    elif segment.kind == "circle":
        x, y, radius = segment.values
        modelspace.add_circle((x, y, 0), radius=radius, dxfattribs={"layer": segment.layer})
    elif segment.kind == "arc":
        x, y, radius, start_angle, end_angle = segment.values
        modelspace.add_arc(
            center=(x, y, 0),
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
            dxfattribs={"layer": segment.layer},
        )
    else:
        raise ValueError(f"Неизвестный тип линии: {segment.kind}")


def create_dxf_document(params):
    validate_params(params)
    verify_assembly(params)

    document = ezdxf.new("R2010")
    document.header["$INSUNITS"] = 4
    modelspace = document.modelspace()
    add_layer(document, "CUT")

    for panel in build_panels(params):
        for segment in panel.segments:
            add_segment(document, modelspace, segment)

    return document


def save_dxf_file(params, path):
    document = create_dxf_document(params)
    document.saveas(path)


def write_example_files(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for thickness, kerf in [(3.0, 0.12), (4.0, 0.15)]:
        params = BoxParams(thickness=thickness, kerf=kerf)
        path = output_dir / f"montazhny_korob_{fmt(thickness)}mm.dxf"
        save_dxf_file(params, path)
        paths.append(path)
    return paths
