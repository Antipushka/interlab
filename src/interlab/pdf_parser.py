from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import fitz

from .model import PageModel, Style, TextSpan, VectorObject


def _point(value: Any) -> list[float]:
    return [float(value.x), float(value.y)]


def _item(item: tuple) -> dict[str, Any]:
    kind = item[0]
    if kind == "l":
        return {"type": "line", "p1": _point(item[1]), "p2": _point(item[2])}
    if kind == "c":
        return {"type": "cubic", "p1": _point(item[1]), "c1": _point(item[2]), "c2": _point(item[3]), "p2": _point(item[4])}
    if kind == "qu":
        return {"type": "quad", "p1": _point(item[1]), "c": _point(item[2]), "p2": _point(item[3])}
    if kind == "re":
        r = item[1]
        return {"type": "rect", "rect": [r.x0, r.y0, r.x1, r.y1], "orientation": item[2] if len(item) > 2 else None}
    return {"type": kind, "values": [str(x) for x in item[1:]]}


def extract_page(page: fitz.Page) -> PageModel:
    vectors = []
    for n, path in enumerate(page.get_drawings(extended=True)):
        vectors.append(VectorObject(
            id=f"v{n}", items=[_item(x) for x in path.get("items", [])],
            style=Style(
                stroke=list(path["color"]) if path.get("color") is not None else None,
                fill=list(path["fill"]) if path.get("fill") is not None else None,
                width=float(path.get("width") or 0), dashes=path.get("dashes"),
                line_cap=path.get("lineCap"), line_join=path.get("lineJoin"),
                opacity=float(path.get("stroke_opacity", 1)), fill_opacity=float(path.get("fill_opacity", 1))),
            rect=list(path["rect"]), close_path=bool(path.get("closePath")),
            layer=path.get("layer"), clip=path.get("scissor"), source_ids=[f"v{n}"]))
    texts = []
    raw = page.get_text("rawdict")
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            direction = list(line.get("dir", (1, 0)))
            for span in line.get("spans", []):
                chars = span.get("chars", [])
                content = "".join(c.get("c", "") for c in chars)
                if not content:
                    continue
                origin = list(chars[0].get("origin", span.get("origin", (0, 0))))
                texts.append(TextSpan(
                    id=f"t{len(texts)}", text=content, origin=origin, bbox=list(span["bbox"]),
                    font=span.get("font", "sans-serif"), size=float(span.get("size", 10)),
                    color=int(span.get("color", 0)), flags=int(span.get("flags", 0)),
                    direction=direction, matrix=[direction[0], direction[1], -direction[1], direction[0], origin[0], origin[1]]))
    return PageModel(float(page.rect.width), float(page.rect.height), vectors, texts)


def inspect_pdf(path: Path) -> tuple[dict[str, Any], PageModel]:
    doc = fitz.open(path)
    pages = []
    first = None
    for index, page in enumerate(doc):
        model = extract_page(page)
        if first is None:
            first = model
        widths, strokes, fills, dashes, primitives, fonts, rotations, caps, joins = (Counter() for _ in range(9))
        for obj in model.vectors:
            widths[round(obj.style.width, 6)] += 1
            strokes[str(obj.style.stroke)] += 1; fills[str(obj.style.fill)] += 1
            dashes[str(obj.style.dashes)] += 1
            caps[str(obj.style.line_cap)] += 1; joins[str(obj.style.line_join)] += 1
            primitives.update(x["type"] for x in obj.items)
        for text in model.texts:
            fonts[text.font] += 1
            rotations[round(__import__("math").degrees(__import__("math").atan2(text.direction[1], text.direction[0])), 3)] += 1
        pages.append({"page": index + 1, "dimensions_pt": [model.width, model.height],
            "vector_object_count": len(model.vectors), "primitive_count": sum(len(x.items) for x in model.vectors),
            "text_span_count": len(model.texts), "text_character_count": sum(len(x.text) for x in model.texts),
            "image_count": len(page.get_images(full=True)), "stroke_widths": dict(widths), "stroke_colors": dict(strokes),
            "fills": dict(fills), "dash_patterns": dict(dashes), "primitive_types": dict(primitives),
            "line_caps": dict(caps), "line_joins": dict(joins),
            "clipping": {"available": True, "objects_with_scissor": sum(x.clip is not None for x in model.vectors)},
            "fonts": dict(fonts), "text_rotations_degrees": dict(rotations),
            "text_transforms": dict(Counter(str(x.matrix) for x in model.texts))})
    if first is None:
        raise ValueError("PDF has no pages")
    return {"source": str(path), "page_count": len(doc), "pages": pages}, first
