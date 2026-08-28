from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .model import Style, VectorObject


_NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def normalize_numeric_enum(
    value: Any, allowed: set[int], field_name: str
) -> int | None:
    """Normalize PyMuPDF's integer-like style enums without lossy coercion."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be an integer enum or None, got {value!r}")
    numeric = _number(value)
    if numeric is None or not numeric.is_integer():
        raise ValueError(f"{field_name} must be an integral finite value, got {value!r}")
    normalized = int(numeric)
    if normalized not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)} or None, got {value!r}"
        )
    return normalized


def normalize_line_cap(value: Any) -> int | None:
    """Collapse equal PyMuPDF cap tuples; reject unrepresentable mixed caps."""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        caps = [normalize_numeric_enum(item, {0, 1, 2}, "lineCap") for item in value]
        if not caps:
            return None
        if len(set(caps)) != 1:
            raise ValueError(
                f"lineCap contains different cap styles {value!r}; one SVG stroke-linecap cannot represent them losslessly"
            )
        return caps[0]
    return normalize_numeric_enum(value, {0, 1, 2}, "lineCap")


def _finite_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a finite number, got {value!r}")
    number = _number(value)
    if number is None:
        raise ValueError(f"{field_name} must be a finite number, got {value!r}")
    return number


def normalize_dashes(value: Any) -> tuple[list[float] | None, float]:
    """Normalize PyMuPDF ``[dash array] phase`` strings and sequence forms."""
    if value is None:
        return None, 0.0
    offset: Any = 0.0
    if isinstance(value, str):
        match = re.fullmatch(
            rf"\s*\[\s*((?:{_NUMBER_PATTERN}(?:\s+{_NUMBER_PATTERN})*)?)\s*\]\s*({_NUMBER_PATTERN})\s*",
            value,
        )
        if match is None:
            raise ValueError(f"dashes has unsupported PyMuPDF representation {value!r}")
        raw_pattern = [float(item) for item in match.group(1).split()] if match.group(1) else []
        offset = float(match.group(2))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) == 2 and isinstance(value[0], Sequence) and not isinstance(value[0], (str, bytes)):
            raw_pattern, offset = value
        else:
            raw_pattern = value
    else:
        raise ValueError(f"dashes has unsupported PyMuPDF representation {value!r}")
    pattern = [_finite_number(item, "dash length") for item in raw_pattern]
    if any(item < 0 for item in pattern):
        raise ValueError(f"dash lengths must be non-negative, got {value!r}")
    normalized_offset = _finite_number(offset, "dash offset")
    return (pattern or None), normalized_offset


def _normalize_color(value: Any, field_name: str) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field_name} must be a numeric color sequence or None, got {value!r}")
    color = [_finite_number(component, field_name) for component in value]
    if not color or any(component < 0 or component > 1 for component in color):
        raise ValueError(f"{field_name} components must be within [0, 1], got {value!r}")
    return color


def _normalize_opacity(value: Any, field_name: str) -> float:
    opacity = _finite_number(value, field_name)
    if opacity < 0 or opacity > 1:
        raise ValueError(f"{field_name} must be within [0, 1], got {value!r}")
    return opacity


def _normalize_close_path(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value in (0, 1):
        return bool(value)
    raise ValueError(f"closePath must be boolean, 0, 1, or None, got {value!r}")


def _point(value: Any) -> list[float] | None:
    if hasattr(value, "x") and hasattr(value, "y"):
        x, y = _number(value.x), _number(value.y)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2:
        x, y = _number(value[0]), _number(value[1])
    else:
        return None
    return [x, y] if x is not None and y is not None else None


def _rect(value: Any) -> list[float] | None:
    if all(hasattr(value, key) for key in ("x0", "y0", "x1", "y1")):
        values = [value.x0, value.y0, value.x1, value.y1]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 4:
        values = list(value)
    else:
        return None
    numbers = [_number(item) for item in values]
    if any(item is None for item in numbers):
        return None
    x0, y0, x1, y1 = numbers
    return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]


def _quad(value: Any) -> list[list[float]] | None:
    if all(hasattr(value, key) for key in ("ul", "ur", "ll", "lr")):
        raw = [value.ul, value.ur, value.lr, value.ll]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 4:
        # PyMuPDF Quad iteration order is ul, ur, ll, lr. Reorder it to walk
        # around the perimeter instead of crossing the quadrilateral.
        raw = [value[0], value[1], value[3], value[2]]
    else:
        return None
    points = [_point(item) for item in raw]
    return points if all(point is not None for point in points) else None


def _json_value(value: Any) -> Any:
    point = _point(value)
    if point is not None:
        return point
    rect = _rect(value)
    if rect is not None:
        return rect
    quad = _quad(value)
    if quad is not None:
        return quad
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _unsupported(item: Any, source_type: str, reason: str) -> dict[str, Any]:
    values = list(item[1:]) if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) else [item]
    return {
        "type": "unsupported",
        "source_type": source_type,
        "reason": reason,
        "values": _json_value(values),
    }


def parse_item(item: Any) -> tuple[dict[str, Any], bool, str]:
    if not isinstance(item, Sequence) or isinstance(item, (str, bytes)) or not item:
        return _unsupported(item, "invalid", "primitive is not a non-empty sequence"), False, "invalid"
    kind = str(item[0])
    if kind == "l" and len(item) == 3:
        p1, p2 = _point(item[1]), _point(item[2])
        if p1 is not None and p2 is not None:
            return {"type": "line", "p1": p1, "p2": p2}, True, kind
    elif kind == "c" and len(item) == 5:
        points = [_point(value) for value in item[1:]]
        if all(point is not None for point in points):
            p1, c1, c2, p2 = points
            return {"type": "cubic", "p1": p1, "c1": c1, "c2": c2, "p2": p2}, True, kind
    elif kind == "re" and len(item) >= 2:
        rect = _rect(item[1])
        if rect is not None:
            return {
                "type": "rect",
                "rect": rect,
                "orientation": _json_value(item[2]) if len(item) > 2 else None,
            }, True, kind
    elif kind == "qu" and len(item) == 2:
        points = _quad(item[1])
        if points is not None:
            return {"type": "quad", "points": points}, True, kind
    reason = "unknown primitive type" if kind not in {"l", "c", "re", "qu"} else "malformed primitive tuple"
    return _unsupported(item, kind, reason), False, kind


def _item_points(item: dict[str, Any]) -> list[list[float]]:
    kind = item["type"]
    if kind == "line":
        return [item["p1"], item["p2"]]
    if kind == "cubic":
        return [item["p1"], item["c1"], item["c2"], item["p2"]]
    if kind == "rect":
        x0, y0, x1, y1 = item["rect"]
        return [[x0, y0], [x1, y1]]
    if kind == "quad":
        return item["points"]
    return []


def drawing_bbox(path: Mapping[str, Any], items: list[dict[str, Any]]) -> tuple[list[float], bool]:
    for key in ("rect", "bbox"):
        native = _rect(path.get(key))
        if native is not None:
            return native, False
    points = [point for item in items for point in _item_points(item)]
    if not points:
        raise ValueError(
            "drawing has neither a valid native rect/bbox nor supported geometry from which to calculate one"
        )
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [min(xs), min(ys), max(xs), max(ys)], True


def parse_drawing(path: Mapping[str, Any], identifier: str, telemetry: dict[str, Any]) -> VectorObject:
    raw_items = path.get("items")
    if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
        raw_items = []
    items = []
    for raw_item in raw_items:
        item, supported, source_type = parse_item(raw_item)
        items.append(item)
        telemetry["primitive_types_encountered"][source_type] += 1
        if not supported:
            telemetry["unsupported_primitive_count"] += 1

    if _rect(path.get("rect")) is None:
        telemetry["drawings_without_native_rect"] += 1
    rect, calculated = drawing_bbox(path, items)
    if calculated:
        telemetry["bboxes_calculated_from_primitives"] += 1

    stroke_opacity = path.get("stroke_opacity", path.get("opacity", 1.0))
    fill_opacity = path.get("fill_opacity", path.get("opacity", 1.0))
    width = _finite_number(path.get("width", 0) or 0, "width")
    if width < 0:
        raise ValueError(f"width must be non-negative, got {path.get('width')!r}")
    dashes, dash_offset = normalize_dashes(path.get("dashes"))
    return VectorObject(
        id=identifier,
        items=items,
        style=Style(
            stroke=_normalize_color(path.get("color"), "color"),
            fill=_normalize_color(path.get("fill"), "fill"),
            width=width,
            dashes=dashes,
            dash_offset=dash_offset,
            line_cap=normalize_line_cap(path.get("lineCap")),
            line_join=normalize_numeric_enum(path.get("lineJoin"), {0, 1, 2}, "lineJoin"),
            opacity=_normalize_opacity(stroke_opacity if stroke_opacity is not None else 1.0, "stroke_opacity"),
            fill_opacity=_normalize_opacity(fill_opacity if fill_opacity is not None else 1.0, "fill_opacity"),
        ),
        rect=rect,
        close_path=_normalize_close_path(path.get("closePath")),
        layer=path.get("layer"),
        clip=_json_value(path.get("scissor")),
        source_ids=[identifier],
        sequence_number=path.get("seqno"),
    )
