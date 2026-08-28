from collections import Counter

import pytest

from interlab.drawing_parser import drawing_bbox, parse_drawing, parse_item
from interlab.svg_exporter import _path


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Rect:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1


class Quad:
    def __init__(self, ul, ur, ll, lr):
        self.ul, self.ur, self.ll, self.lr = ul, ur, ll, lr


def telemetry():
    return {
        "drawings_without_native_rect": 0,
        "bboxes_calculated_from_primitives": 0,
        "unsupported_primitive_count": 0,
        "primitive_types_encountered": Counter(),
    }


def test_drawing_without_rect_keeps_line_and_calculates_bbox():
    stats = telemetry()
    drawing = parse_drawing(
        {"items": [("l", Point(9, 4), Point(2, 8))], "color": None}, "v0", stats
    )

    assert drawing.items == [{"type": "line", "p1": [9.0, 4.0], "p2": [2.0, 8.0]}]
    assert drawing.rect == [2.0, 4.0, 9.0, 8.0]
    assert stats["drawings_without_native_rect"] == 1
    assert stats["bboxes_calculated_from_primitives"] == 1
    assert stats["primitive_types_encountered"] == Counter({"l": 1})


def test_rectangle_cubic_and_quad_are_parsed_type_aware():
    rectangle, rect_supported, _ = parse_item(("re", Rect(7, 8, 1, 2), 1))
    cubic, cubic_supported, _ = parse_item(
        ("c", Point(0, 0), Point(1, 3), Point(2, 3), Point(4, 0))
    )
    quad, quad_supported, _ = parse_item(
        ("qu", Quad(Point(0, 0), Point(4, 0), Point(0, 3), Point(4, 3)))
    )

    assert rectangle == {"type": "rect", "rect": [1.0, 2.0, 7.0, 8.0], "orientation": 1}
    assert cubic["type"] == "cubic" and cubic["c2"] == [2.0, 3.0]
    assert quad == {
        "type": "quad",
        "points": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]],
    }
    assert rect_supported and cubic_supported and quad_supported
    assert drawing_bbox({}, [rectangle, cubic, quad]) == ([0.0, 0.0, 7.0, 8.0], True)


def test_unknown_primitive_is_preserved_and_counted_not_silently_deleted():
    stats = telemetry()
    drawing = parse_drawing(
        {"rect": Rect(1, 2, 3, 4), "items": [("future", Point(1, 2), Point(3, 4))]},
        "v7",
        stats,
    )

    assert len(drawing.items) == 1
    assert drawing.items[0]["type"] == "unsupported"
    assert drawing.items[0]["source_type"] == "future"
    assert drawing.items[0]["values"] == [[1.0, 2.0], [3.0, 4.0]]
    assert stats["unsupported_primitive_count"] == 1
    assert stats["primitive_types_encountered"] == Counter({"future": 1})


def test_missing_bbox_and_usable_geometry_fails_explicitly():
    with pytest.raises(ValueError, match="neither a valid native rect/bbox"):
        parse_drawing({"items": [("future", "opaque")]}, "v8", telemetry())


def test_pymupdf_quad_exports_as_closed_four_sided_path():
    drawing = parse_drawing(
        {
            "items": [
                ("qu", Quad(Point(0, 0), Point(4, 0), Point(0, 3), Point(4, 3)))
            ]
        },
        "v9",
        telemetry(),
    )

    assert _path(drawing) == (
        "M 0.000000 0.000000 L 4.000000 0.000000 "
        "L 4.000000 3.000000 L 0.000000 3.000000 Z"
    )


def test_unsupported_primitive_stops_svg_export_with_explicit_error():
    drawing = parse_drawing(
        {"rect": Rect(1, 2, 3, 4), "items": [("future", Point(1, 2))]},
        "v10",
        telemetry(),
    )

    with pytest.raises(ValueError, match="cannot losslessly export primitive 'future'"):
        _path(drawing)
