from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def analyze_reference(reference: Path, pdf_preview: Path, page_width: float, page_height: float,
                      alignment_output: Path, seeds_output: Path, overlay_output: Path) -> dict:
    """Register the coloured semantic reference against a PDF rendering.

    Registration uses only the desaturated architectural ink.  Coloured pixels
    are subsequently transformed as approximate seeds and never become PDF
    geometry.
    """
    rgb = np.asarray(Image.open(reference).convert("RGB")); h, w = rgb.shape[:2]
    target = np.asarray(Image.open(pdf_preview).convert("RGB")); th, tw = target.shape[:2]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    color_mask = ((hsv[..., 1] > 55) & (hsv[..., 2] > 40)).astype(np.uint8) * 255
    ref_gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    ref_gray[color_mask > 0] = 255
    ref_ink = 255 - ref_gray
    target_ink = 255 - cv2.cvtColor(target, cv2.COLOR_RGB2GRAY)

    # Initial full-image affine, refined by ECC to account for crop / padding.
    initial = np.array([[tw / w, 0, 0], [0, th / h, 0]], dtype=np.float32)
    warp = initial.copy()
    score = None
    try:
        score, warp = cv2.findTransformECC(target_ink.astype(np.float32) / 255,
            ref_ink.astype(np.float32) / 255, warp, cv2.MOTION_AFFINE,
            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), None, 5)
    except cv2.error:
        pass

    nz = cv2.findNonZero((ref_gray < 245).astype(np.uint8))
    content = list(map(int, cv2.boundingRect(nz))) if nz is not None else None
    contours, _ = cv2.findContours(cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE,
        np.ones((5, 5), np.uint8)), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    sx, sy = page_width / tw, page_height / th
    regions = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = float(cv2.contourArea(contour))
        if area < max(50, w * h * .0001): continue
        raw = cv2.approxPolyDP(contour, max(1, cv2.arcLength(contour, True) * .002), True).reshape(-1, 2)
        if len(raw) < 3: continue
        transformed_px = cv2.transform(raw.reshape(1, -1, 2).astype(np.float32), warp)[0]
        polygon_ref = raw.astype(float).tolist()
        polygon_pdf = [[float(x*sx), float(y*sy)] for x, y in transformed_px]
        moments=cv2.moments(contour); cx=moments["m10"]/moments["m00"]; cy=moments["m01"]/moments["m00"]
        pixels=rgb[cv2.drawContours(np.zeros((h,w),np.uint8),[contour],-1,255,-1)>0]
        representative=np.median(pixels,axis=0).astype(int).tolist()
        xs=[p[0] for p in polygon_pdf]; ys=[p[1] for p in polygon_pdf]
        regions.append({"seed_id":f"apartment_seed_{len(regions)+1:02d}","representative_color_rgb":representative,
            "reference_polygon":polygon_ref,"transformed_pdf_polygon":polygon_pdf,"polygon_pdf":polygon_pdf,
            "bbox_pdf":[min(xs),min(ys),max(xs),max(ys)],"centroid_reference_px":[cx,cy],
            "area_reference_px":area,"confidence":float(max(0,min(1,score or 0)))})

    overlay=target.copy(); warped=cv2.warpAffine(rgb,warp,(tw,th),flags=cv2.INTER_LINEAR,borderValue=(255,255,255))
    warped_mask=cv2.warpAffine(color_mask,warp,(tw,th))>0
    overlay[warped_mask]=(overlay[warped_mask]*.45+warped[warped_mask]*.55).astype(np.uint8)
    Image.fromarray(overlay).save(overlay_output)
    matrix_pdf=[[float(warp[0,0]*sx),float(warp[0,1]*sx),float(warp[0,2]*sx)],
                [float(warp[1,0]*sy),float(warp[1,1]*sy),float(warp[1,2]*sy)]]
    alignment={"reference":str(reference),"reference_dimensions_px":[w,h],"pdf_preview_dimensions_px":[tw,th],
        "reference_content_bounds_xywh":content,"method":"architectural-ink ECC affine",
        "matrix_reference_to_pdf":matrix_pdf,"ecc_score":score,"rotation_or_shear_present":bool(abs(warp[0,1])>1e-4 or abs(warp[1,0])>1e-4)}
    alignment_output.write_text(json.dumps(alignment,ensure_ascii=False,indent=2),encoding="utf-8")
    report={"alignment":alignment,"colored_regions_detected":len(regions),"regions":regions}
    seeds_output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report
