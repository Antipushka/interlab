from __future__ import annotations

from shapely.geometry import Point, Polygon, box

from .model import PageModel


def select_apartment(model: PageModel, points: list[list[float]]):
    seed = Polygon(points)
    band = max(model.width, model.height) * 0.003
    inner = seed.buffer(-band); boundary = seed.boundary.buffer(band)
    vectors, ownership, ambiguous = [], {}, []
    for obj in model.vectors:
        geom = box(*obj.rect)
        if inner.intersects(geom): relation = "inside"
        elif boundary.intersects(geom):
            relation = "boundary"; ambiguous.append({"object_id":obj.id,"candidate_relations":["boundary","shared"],"reason":"seed is approximate"})
        else: continue
        vectors.append(obj); ownership[obj.id] = relation
    texts = [t for t in model.texts if seed.covers(Point(t.origin))]
    return PageModel(model.width, model.height, vectors, texts), ownership, ambiguous

