from box_geometry import load_svg_text, validate_params, verify_assembly


def save_svg_file(params, path):
    validate_params(params)
    verify_assembly(params)
    path.write_text(load_svg_text(params), encoding="utf-8")
