from __future__ import annotations

from copy import deepcopy
from math import hypot

from .model import PageModel, VectorObject


def _style_key(obj: VectorObject):
    s = obj.style
    return (str(s.stroke), str(s.fill), round(s.width, 6), s.dashes, str(s.line_cap), str(s.line_join), s.opacity, s.fill_opacity, obj.close_path)


def normalize(model: PageModel, tolerance: float = 1e-5) -> tuple[PageModel, dict]:
    """Only exact duplicate removal and provably collinear contiguous single lines."""
    unique, seen, duplicates = [], {}, 0
    for obj in model.vectors:
        key = (_style_key(obj), str(obj.items))
        if key in seen:
            seen[key].source_ids.extend(obj.source_ids); duplicates += 1
        else:
            clone = deepcopy(obj); unique.append(clone); seen[key] = clone

    # Repeated passes merge only endpoint-touching lines with equal style.
    merged_count = 0
    changed = True
    while changed:
        changed = False
        endpoint_map = {}
        for i, obj in enumerate(unique):
            if len(obj.items) == 1 and obj.items[0]["type"] == "line":
                line = obj.items[0]
                for p in (line["p1"], line["p2"]): endpoint_map.setdefault((round(p[0], 5), round(p[1], 5), _style_key(obj)), []).append(i)
        for ids in endpoint_map.values():
            if len(ids) != 2: continue
            a, b = ids
            if a == b: continue
            oa, ob = unique[a], unique[b]; la, lb = oa.items[0], ob.items[0]
            common = next((p for p in (la["p1"], la["p2"]) for q in (lb["p1"], lb["p2"]) if hypot(p[0]-q[0], p[1]-q[1]) <= tolerance), None)
            if common is None: continue
            pa = la["p2"] if la["p1"] == common else la["p1"]
            pb = lb["p2"] if lb["p1"] == common else lb["p1"]
            cross = (common[0]-pa[0])*(pb[1]-common[1])-(common[1]-pa[1])*(pb[0]-common[0])
            scale = max(1.0, hypot(common[0]-pa[0], common[1]-pa[1]), hypot(pb[0]-common[0], pb[1]-common[1]))
            if abs(cross) > tolerance * scale: continue
            # The common endpoint must lie between the two remaining endpoints.
            # Otherwise two overlapping rays would be incorrectly enlarged.
            dot = (pa[0]-common[0])*(pb[0]-common[0]) + (pa[1]-common[1])*(pb[1]-common[1])
            if dot >= 0: continue
            oa.items = [{"type":"line", "p1":pa, "p2":pb}]; oa.source_ids += ob.source_ids
            oa.rect = [min(pa[0],pb[0]), min(pa[1],pb[1]), max(pa[0],pb[0]), max(pa[1],pb[1])]
            unique.pop(b); merged_count += 1; changed = True; break
    result = PageModel(model.width, model.height, unique, deepcopy(model.texts))
    return result, {"removed_exact_duplicates": duplicates, "merged_collinear_segments": merged_count,
        # Backwards-compatible keys used by the first prototype.
        "duplicates_removed": duplicates, "collinear_merges": merged_count,
        "input_objects": len(model.vectors), "output_objects": len(unique),
        "reduction_percent": (100 * (len(model.vectors)-len(unique))/len(model.vectors)) if model.vectors else 0}
