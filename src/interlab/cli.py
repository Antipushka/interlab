from __future__ import annotations

import argparse, hashlib, json
from collections import Counter
from pathlib import Path

from .apartment_extractor import select_apartment
from .normalizer import normalize
from .pdf_parser import inspect_pdf
from .reference_alignment import analyze_reference
from .svg_exporter import export_svg
from .validator import validate


def main(argv=None):
    p=argparse.ArgumentParser(description="Architectural PDF phase-one pipeline")
    p.add_argument("pdf",type=Path); p.add_argument("reference",type=Path,nargs="?")
    p.add_argument("--output",type=Path,default=Path("output")); args=p.parse_args(argv)
    if not args.pdf.is_file(): p.error(f"PDF not found: {args.pdf}")
    before=hashlib.sha256(args.pdf.read_bytes()).hexdigest(); args.output.mkdir(parents=True,exist_ok=True)
    diagnostics, extracted=inspect_pdf(args.pdf)
    (args.output/"diagnostics.json").write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding="utf-8")
    (args.output/"page_01_extracted.json").write_text(json.dumps(extracted.dict(),ensure_ascii=False,indent=2),encoding="utf-8")
    normalized,norm_stats=normalize(extracted)
    (args.output/"page_01_normalized.json").write_text(json.dumps(normalized.dict(),ensure_ascii=False,indent=2),encoding="utf-8")
    ext_svg=args.output/"page_01_extracted.svg"; norm_svg=args.output/"page_01_normalized.svg"
    export_svg(extracted,ext_svg); export_svg(normalized,norm_svg)
    primitive_count=sum(len(x.items) for x in extracted.vectors)
    reduction=len(extracted.vectors)-len(normalized.vectors)
    stats={"original_drawing_objects":len(extracted.vectors),"original_primitive_count":primitive_count,
        "extracted_svg_vector_element_count":len(extracted.vectors),"normalized_svg_vector_element_count":len(normalized.vectors),
        "total_reduction_count":reduction,"reduction_percentage":100*reduction/len(extracted.vectors) if extracted.vectors else 0,
        "text_element_count_before_normalization":len(extracted.texts),"text_element_count_after_normalization":len(normalized.texts),**norm_stats}
    (args.output/"page_01_normalization_stats.json").write_text(json.dumps(stats,indent=2),encoding="utf-8")
    validation=validate(args.pdf,ext_svg,norm_svg,args.output,stats)
    apartment_created=False
    if args.reference:
        validation_dir=args.output/"validation"
        seeds=analyze_reference(args.reference,validation_dir/"page_01_original.png",extracted.width,extracted.height,
            args.output/"page_01_reference_alignment.json",args.output/"page_01_apartment_seeds.json",
            validation_dir/"page_01_reference_alignment_overlay.png")
        if seeds["regions"]:
            apartment,ownership,ambiguous=select_apartment(extracted,seeds["regions"][0]["polygon_pdf"])
            apartment_dir=args.output/"page_01"; apartment_dir.mkdir(exist_ok=True)
            apartment_svg=apartment_dir/"apartment_test_01.svg"; export_svg(apartment,apartment_svg,ownership)
            import cairosvg
            cairosvg.svg2png(url=str(apartment_svg),write_to=str(apartment_dir/"apartment_test_01.png"),output_width=validation["render_dimensions_px"][0],output_height=validation["render_dimensions_px"][1])
            counts=Counter(ownership.values())
            apartment_report={"seed_id":seeds["regions"][0]["seed_id"],"total_source_objects_considered":len(extracted.vectors)+len(extracted.texts),
                "inside_count":counts["inside"],"boundary_count":counts["boundary"],"shared_candidate_count":counts["shared_candidate"],
                "exclude_count":counts["exclude"],"global_count":counts["global"],"text_element_count":len(apartment.texts),
                "vector_element_count":len(apartment.vectors),"ambiguous_objects":ambiguous,
                "classification_policy":"whole-object; uncertain boundary geometry is retained; seed is not a clipping path"}
            (apartment_dir/"apartment_test_01.json").write_text(json.dumps(apartment_report,ensure_ascii=False,indent=2),encoding="utf-8")
            apartment_created=True
    after=hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    summary={"source_sha256_before":before,"source_sha256_after":after,"source_immutable":before==after,"normalization":stats,"validation":validation,"apartment_created":apartment_created}
    (args.output/"run_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__": main()
