from __future__ import annotations

import argparse, hashlib, json
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
    stats={"original_drawing_objects":len(extracted.vectors),"extracted_svg_vector_elements":len(extracted.vectors),
        "normalized_svg_vector_elements":len(normalized.vectors),"text_elements":len(extracted.texts),**norm_stats}
    validation=validate(args.pdf,ext_svg,norm_svg,args.output,stats)
    apartment_created=False
    if args.reference:
        seeds=analyze_reference(args.reference,extracted.width,extracted.height,args.output/"page_01_apartment_seeds.json")
        if seeds["regions"]:
            apartment,ownership,ambiguous=select_apartment(extracted,seeds["regions"][0]["polygon_pdf"])
            apartment_dir=args.output/"page_01"; apartment_dir.mkdir(exist_ok=True)
            export_svg(apartment,apartment_dir/"apartment_test_01.svg",ownership)
            (apartment_dir/"apartment_test_01_ownership.json").write_text(json.dumps({"policy":"whole-object, many-to-many-ready","ownership":ownership,"ambiguous":ambiguous},indent=2),encoding="utf-8")
            apartment_created=True
    after=hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    summary={"source_immutable":before==after,"normalization":norm_stats,"validation":validation,"apartment_created":apartment_created}
    (args.output/"run_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__": main()

