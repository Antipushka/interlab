from __future__ import annotations

import json
from pathlib import Path

import cairosvg
import pymupdf as fitz
import numpy as np
from PIL import Image, ImageChops


def validate(pdf: Path, extracted_svg: Path, normalized_svg: Path, output: Path, stats: dict) -> dict:
    output=output.resolve(); validation=output/"validation"; validation.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(pdf); page=doc[0]; pix=page.get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
    original=validation/"page_01_original.png"; pix.save(original)
    width,height=pix.width,pix.height
    ext=validation/"page_01_extracted.png"; norm=validation/"page_01_normalized.png"
    cairosvg.svg2png(url=str(extracted_svg),write_to=str(ext),output_width=width,output_height=height)
    cairosvg.svg2png(url=str(normalized_svg),write_to=str(norm),output_width=width,output_height=height)
    base=Image.open(original).convert("RGB")
    result={"render_dimensions_px":[width,height],"statistics":stats,"comparisons":{}}
    for name,path in (("extracted",ext),("normalized",norm)):
        other=Image.open(path).convert("RGB"); delta=ImageChops.difference(base,other)
        arr=np.asarray(delta,dtype=np.float32)
        significant=np.any(arr>8,axis=2); ys,xs=np.where(significant)
        diff=validation/f"page_01_{name}_diff.png"; delta.save(diff)
        bbox=None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
        result["comparisons"][name]={"MAE":float(arr.mean()),"different_pixel_percent":float(significant.mean()*100),
            "maximum_difference":int(arr.max()),"significant_difference_bbox_px":bbox,"diff":str(diff)}
    (validation/"validation.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
