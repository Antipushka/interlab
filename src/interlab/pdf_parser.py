from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pymupdf as fitz

from .drawing_parser import parse_drawing
from .model import PageModel, TextSpan


def extract_page(page: fitz.Page, telemetry: dict[str, Any] | None = None) -> PageModel:
    if telemetry is None:
        telemetry = {
            "drawings_without_native_rect": 0,
            "bboxes_calculated_from_primitives": 0,
            "unsupported_primitive_count": 0,
            "primitive_types_encountered": Counter(),
        }
    vectors = []
    for n, path in enumerate(page.get_drawings(extended=True)):
        vectors.append(parse_drawing(path, f"v{n}", telemetry))
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
        drawing_parse = {
            "drawings_without_native_rect": 0,
            "bboxes_calculated_from_primitives": 0,
            "unsupported_primitive_count": 0,
            "primitive_types_encountered": Counter(),
        }
        model = extract_page(page, drawing_parse)
        if first is None:
            first = model
        widths, strokes, fills, dashes, primitives, fonts, rotations, caps, joins = (Counter() for _ in range(9))
        for obj in model.vectors:
            widths[round(obj.style.width, 6)] += 1
            strokes[str(obj.style.stroke)] += 1; fills[str(obj.style.fill)] += 1
            dashes[str((obj.style.dashes, obj.style.dash_offset))] += 1
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
            "drawing_parse": {**drawing_parse, "primitive_types_encountered": dict(drawing_parse["primitive_types_encountered"])},
            "clipping": {"available": True, "objects_with_scissor": sum(x.clip is not None for x in model.vectors)},
            "fonts": dict(fonts), "text_rotations_degrees": dict(rotations),
            "text_transforms": dict(Counter(str(x.matrix) for x in model.texts))})
    if first is None:
        raise ValueError("PDF has no pages")
    return {"source": str(path), "page_count": len(doc), "pages": pages}, first
