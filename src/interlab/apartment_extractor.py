from __future__ import annotations

from shapely.geometry import Point, Polygon, box

from .model import PageModel


def select_apartment(model: PageModel, points: list[list[float]]):
    """Classify every source object; retain doubtful boundary objects whole."""
    seed = Polygon(points).buffer(0); band = max(model.width, model.height) * .004
    inner=seed.buffer(-band); outer=seed.buffer(band); vectors=[]; ownership={}; ambiguous=[]
    for obj in model.vectors:
        geom=box(*obj.rect)
        if seed.contains(geom): relation="inside"
        elif inner.intersects(geom) and not seed.contains(geom): relation="boundary"
        elif outer.intersects(geom):
            relation="shared_candidate"
            ambiguous.append({"object_id":obj.id,"candidate_relations":["boundary","shared_candidate"],"reason":"whole PDF object intersects approximate seed band"})
        elif geom.area >= model.width*model.height*.5: relation="global"
        else: relation="exclude"
        ownership[obj.id]=relation
        if relation != "exclude": vectors.append(obj)
    texts=[]
    for text in model.texts:
        relation="inside" if seed.covers(Point(text.origin)) else "exclude"
        ownership[text.id]=relation
        if relation != "exclude": texts.append(text)
    return PageModel(model.width,model.height,vectors,texts),ownership,ambiguous
