from __future__ import annotations

import html
from pathlib import Path

from .model import PageModel, VectorObject


def _color(c, default="none"):
    if c is None: return default
    return "#" + "".join(f"{max(0,min(255,round(x*255))):02x}" for x in c[:3])


def _path(obj: VectorObject):
    out = []
    for x in obj.items:
        if x["type"] == "line": out.append(f'M {x["p1"][0]:.6f} {x["p1"][1]:.6f} L {x["p2"][0]:.6f} {x["p2"][1]:.6f}')
        elif x["type"] == "cubic": out.append(f'M {x["p1"][0]:.6f} {x["p1"][1]:.6f} C {x["c1"][0]:.6f} {x["c1"][1]:.6f} {x["c2"][0]:.6f} {x["c2"][1]:.6f} {x["p2"][0]:.6f} {x["p2"][1]:.6f}')
        elif x["type"] == "rect":
            r=x["rect"]; out.append(f'M {r[0]} {r[1]} H {r[2]} V {r[3]} H {r[0]} Z')
        elif x["type"] == "quad":
            points=x["points"]
            out.append("M " + " L ".join(f"{p[0]:.6f} {p[1]:.6f}" for p in points) + " Z")
        else:
            raise ValueError(
                f'cannot losslessly export primitive {x.get("source_type", x.get("type"))!r}: '
                f'{x.get("reason", "unsupported internal representation")}'
            )
    if obj.close_path: out.append("Z")
    return " ".join(out)


def export_svg(model: PageModel, path: Path, ownership: dict[str,str] | None = None):
    rows = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{model.width}pt" height="{model.height}pt" viewBox="0 0 {model.width} {model.height}">', '<g id="vectors">']
    for obj in model.vectors:
        s=obj.style; attrs = f'stroke="{_color(s.stroke)}" fill="{_color(s.fill)}" stroke-width="{s.width}" stroke-opacity="{s.opacity}" fill-opacity="{s.fill_opacity}"'
        if s.dashes and s.dashes != "[] 0": attrs += f' stroke-dasharray="{html.escape(str(s.dashes))}"'
        cap = s.line_cap[-1] if isinstance(s.line_cap, (list, tuple)) else s.line_cap
        if cap in (0, 1, 2): attrs += f' stroke-linecap="{("butt", "round", "square")[cap]}"'
        if s.line_join in (0, 1, 2): attrs += f' stroke-linejoin="{("miter", "round", "bevel")[s.line_join]}"'
        relation = ownership.get(obj.id) if ownership else None
        sources=html.escape(",".join(obj.source_ids), quote=True)
        rows.append(f'<path id="{obj.id}" d="{_path(obj)}" {attrs} data-source-ids="{sources}" data-ownership="{relation or "global"}"/>')
    rows += ['</g>', '<g id="texts">']
    for t in model.texts:
        color=f'#{t.color & 0xffffff:06x}'; transform=""
        if t.direction != [1.0,0.0] and t.direction != [1,0]: transform=f' transform="matrix({t.direction[0]} {t.direction[1]} {-t.direction[1]} {t.direction[0]} {t.origin[0]} {t.origin[1]})" x="0" y="0"'
        else: transform=f' x="{t.origin[0]}" y="{t.origin[1]}"'
        rows.append(f'<text id="{t.id}"{transform} font-family="{html.escape(t.font)}" font-size="{t.size}" fill="{color}">{html.escape(t.text)}</text>')
    rows += ['</g>', '</svg>']
    path.write_text("\n".join(rows), encoding="utf-8")
