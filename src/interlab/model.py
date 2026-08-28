from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Style:
    stroke: list[float] | None
    fill: list[float] | None
    width: float
    dashes: str | None = None
    line_cap: Any = None
    line_join: Any = None
    opacity: float = 1.0
    fill_opacity: float = 1.0


@dataclass
class VectorObject:
    id: str
    items: list[dict[str, Any]]
    style: Style
    rect: list[float]
    close_path: bool = False
    layer: str | None = None
    clip: Any = None
    source_ids: list[str] = field(default_factory=list)


@dataclass
class TextSpan:
    id: str
    text: str
    origin: list[float]
    bbox: list[float]
    font: str
    size: float
    color: int
    flags: int
    direction: list[float]
    matrix: list[float]


@dataclass
class PageModel:
    width: float
    height: float
    vectors: list[VectorObject]
    texts: list[TextSpan]

    def dict(self) -> dict[str, Any]:
        return asdict(self)

