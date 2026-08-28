from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from shapely.geometry import Polygon


def analyze_reference(reference: Path, page_width: float, page_height: float, output: Path) -> dict:
    rgb = np.asarray(Image.open(reference).convert("RGB"))
    h, w = rgb.shape[:2]
    # Coloured annotation: saturated, non-near-gray pixels. Geometry is only a seed.
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    mask = ((hsv[..., 1] > 70) & (hsv[..., 2] > 45)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    sx, sy = page_width / w, page_height / h
    regions = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        if cv2.contourArea(contour) < max(50, w*h*0.0001): continue
        eps = max(1.0, cv2.arcLength(contour, True) * 0.002)
        points = [[float(p[0][0])*sx, float(p[0][1])*sy] for p in cv2.approxPolyDP(contour, eps, True)]
        if len(points) >= 3 and Polygon(points).is_valid:
            regions.append({"id": f"apartment_seed_{len(regions)+1:02d}", "polygon_pdf": points,
                "area_reference_px": float(cv2.contourArea(contour)), "confidence": "approximate"})
    report = {"reference": str(reference), "reference_dimensions_px": [w,h],
        "alignment": {"method":"full-page affine scale", "matrix_reference_to_pdf":[sx,0,0,sy,0,0],
        "warning":"Assumes reference covers the full PDF page; verify landmarks before production ownership."},
        "colored_regions_detected": len(regions), "regions": regions}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

