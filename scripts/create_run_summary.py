"""Build concise page-one reports from the processing pipeline's JSON outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output

    pipeline = load(output / "run_summary.json")
    diagnostics = load(output / "diagnostics.json")
    normalization = load(output / "page_01_normalization_stats.json")
    validation = load(output / "validation" / "validation.json")
    alignment = load(output / "page_01_reference_alignment.json")
    seeds = load(output / "page_01_apartment_seeds.json")
    apartment = load(output / "page_01" / "apartment_test_01.json")

    page = diagnostics["pages"][0]
    comparisons = validation["comparisons"]
    width, height = validation["render_dimensions_px"]
    pixel_count = width * height

    def differing_pixels(name: str) -> int:
        percentage = comparisons[name]["different_pixel_percent"]
        return round(pixel_count * percentage / 100)

    metrics = {
        "page_01_drawing_objects": page["vector_object_count"],
        "page_01_primitive_count": page["primitive_count"],
        "extracted_svg_vector_elements": normalization["extracted_svg_vector_element_count"],
        "normalized_svg_vector_elements": normalization["normalized_svg_vector_element_count"],
        "reduction_count": normalization["total_reduction_count"],
        "reduction_percentage": normalization["reduction_percentage"],
        "text_count": normalization["text_element_count_after_normalization"],
        "mae_extracted": comparisons["extracted"]["MAE"],
        "mae_normalized": comparisons["normalized"]["MAE"],
        "differing_pixels_extracted": differing_pixels("extracted"),
        "differing_pixels_normalized": differing_pixels("normalized"),
        "detected_apartment_seed_count": seeds["colored_regions_detected"],
        "alignment_score": alignment["ecc_score"],
        "apartment_inside_count": apartment["inside_count"],
        "apartment_boundary_count": apartment["boundary_count"],
        "apartment_shared_candidate_count": apartment["shared_candidate_count"],
        "apartment_exclude_count": apartment["exclude_count"],
        "apartment_global_count": apartment["global_count"],
        "apartment_ambiguous_count": len(apartment["ambiguous_objects"]),
    }
    report = {
        "pdf_sha256": pipeline["source_sha256_after"],
        "source_immutable": pipeline["source_immutable"],
        "apartment_result": "created" if pipeline["apartment_created"] else "failed",
        "metrics": metrics,
    }
    (output / "run_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    labels = [
        ("PDF SHA-256", report["pdf_sha256"]),
        ("Drawing objects", metrics["page_01_drawing_objects"]),
        ("Primitives", metrics["page_01_primitive_count"]),
        ("Extracted vectors", metrics["extracted_svg_vector_elements"]),
        ("Normalized vectors", metrics["normalized_svg_vector_elements"]),
        ("Reduction", f'{metrics["reduction_count"]} ({metrics["reduction_percentage"]:.4f} %)'),
        ("Text elements", metrics["text_count"]),
        ("MAE extracted", metrics["mae_extracted"]),
        ("MAE normalized", metrics["mae_normalized"]),
        ("Differing pixels extracted", metrics["differing_pixels_extracted"]),
        ("Differing pixels normalized", metrics["differing_pixels_normalized"]),
        ("Apartment seeds", metrics["detected_apartment_seed_count"]),
        ("Alignment score", metrics["alignment_score"]),
        ("Apartment result", report["apartment_result"]),
        ("Inside", metrics["apartment_inside_count"]),
        ("Boundary", metrics["apartment_boundary_count"]),
        ("Shared candidates", metrics["apartment_shared_candidate_count"]),
        ("Exclude", metrics["apartment_exclude_count"]),
        ("Global", metrics["apartment_global_count"]),
        ("Ambiguous", metrics["apartment_ambiguous_count"]),
    ]
    markdown = "# Interlab Page 01 Validation\n\n" + "\n".join(
        f"**{label}:** {value}  " for label, value in labels
    )
    (output / "run_summary.md").write_text(markdown + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
