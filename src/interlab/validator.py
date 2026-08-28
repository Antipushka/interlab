from __future__ import annotations

import json
from pathlib import Path

import cairosvg
import fitz
import numpy as np
from PIL import Image, ImageChops


def validate(pdf: Path, extracted_svg: Path, normalized_svg: Path, output: Path, stats: dict) -> dict:
    doc=fitz.open(pdf); page=doc[0]; pix=page.get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
    original=output/"page_01_original.png"; pix.save(original)
    width,height=pix.width,pix.height
    ext=output/"page_01_extracted.png"; norm=output/"page_01_normalized.png"
    cairosvg.svg2png(url=str(extracted_svg),write_to=str(ext),output_width=width,output_height=height)
    cairosvg.svg2png(url=str(normalized_svg),write_to=str(norm),output_width=width,output_height=height)
    base=Image.open(original).convert("RGB")
    result={"render_dimensions_px":[width,height],"statistics":stats,"comparisons":{}}
    for name,path in (("extracted",ext),("normalized",norm)):
        other=Image.open(path).convert("RGB"); delta=ImageChops.difference(base,other)
        arr=np.asarray(delta,dtype=np.float32)
        diff=output/f"page_01_diff_{name}.png"; delta.save(diff)
        result["comparisons"][name]={"mean_absolute_channel_error":float(arr.mean()),"different_pixel_percent":float(np.any(arr>8,axis=2).mean()*100),"diff":str(diff)}
    (output/"validation.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

