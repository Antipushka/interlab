from collections import Counter

import pytest

from interlab.drawing_parser import parse_drawing
from interlab.model import PageModel
from interlab.svg_exporter import export_svg


def telemetry():
    return {
        "drawings_without_native_rect": 0,
        "bboxes_calculated_from_primitives": 0,
        "unsupported_primitive_count": 0,
        "primitive_types_encountered": Counter(),
    }


def drawing_path(**style):
    return {
        "rect": [0, 0, 10, 10],
        "items": [("l", [0, 0], [10, 10])],
        **style,
    }


@pytest.mark.parametrize(
    ("source", "normalized", "svg_value"),
    [
        (0, 0, "miter"),
        (0.0, 0, "miter"),
        (1, 1, "round"),
        (1.0, 1, "round"),
        (2, 2, "bevel"),
        (2.0, 2, "bevel"),
    ],
)
def test_integral_line_join_values_normalize_and_export(tmp_path, source, normalized, svg_value):
    drawing = parse_drawing(drawing_path(lineJoin=source), "v0", telemetry())
    destination = tmp_path / "drawing.svg"

    export_svg(PageModel(10, 10, [drawing], []), destination)

    assert drawing.style.line_join == normalized
    assert isinstance(drawing.style.line_join, int)
    assert f'stroke-linejoin="{svg_value}"' in destination.read_text(encoding="utf-8")


@pytest.mark.parametrize("value", [1.5, float("nan"), True, -1, 3, "1"])
def test_invalid_line_join_is_not_silently_coerced(value):
    with pytest.raises(ValueError, match="lineJoin"):
        parse_drawing(drawing_path(lineJoin=value), "v0", telemetry())


@pytest.mark.parametrize(
    ("value", "normalized", "svg_value"),
    [
        (0, 0, "butt"),
        (0.0, 0, "butt"),
        ((1, 1, 1), 1, "round"),
        ([1.0, 1, 1.0], 1, "round"),
        (2, 2, "square"),
        ((2.0, 2, 2), 2, "square"),
    ],
)
def test_scalar_and_uniform_line_cap_representations_normalize_and_export(
    tmp_path, value, normalized, svg_value
):
    drawing = parse_drawing(drawing_path(lineCap=value), "v0", telemetry())
    destination = tmp_path / "drawing.svg"

    export_svg(PageModel(10, 10, [drawing], []), destination)

    assert drawing.style.line_cap == normalized
    assert isinstance(drawing.style.line_cap, int)
    assert f'stroke-linecap="{svg_value}"' in destination.read_text(encoding="utf-8")


def test_mixed_line_caps_fail_when_one_svg_cap_cannot_preserve_them():
    with pytest.raises(ValueError, match="cannot represent them losslessly"):
        parse_drawing(drawing_path(lineCap=(0, 1, 0)), "v0", telemetry())


@pytest.mark.parametrize(
    ("source", "pattern", "offset"),
    [
        ("[3 2] 1", [3.0, 2.0], 1.0),
        (([3, 2], 1), [3.0, 2.0], 1.0),
        ([3, 2], [3.0, 2.0], 0.0),
    ],
)
def test_dash_representations_normalize_and_export(tmp_path, source, pattern, offset):
    drawing = parse_drawing(drawing_path(dashes=source), "v0", telemetry())
    destination = tmp_path / "drawing.svg"

    export_svg(PageModel(10, 10, [drawing], []), destination)
    svg = destination.read_text(encoding="utf-8")

    assert drawing.style.dashes == pattern
    assert drawing.style.dash_offset == offset
    assert 'stroke-dasharray="3 2"' in svg
    assert f'stroke-dashoffset="{offset:g}"' in svg
