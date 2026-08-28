# Interlab phase-one prototype

This command-line pipeline inspects an architectural PDF, extracts page one to
an editable SVG, conservatively normalizes duplicate/adjacent line segments,
renders visual comparisons, aligns a coloured PNG reference, and makes one
non-destructive apartment ownership experiment.

```bash
python -m pip install -e .
interlab input.pdf reference.png --output output
```

The PDF is opened read-only. The reference is deliberately treated only as a
semantic seed; selected PDF objects are copied whole, boundary candidates are
allowed to belong to multiple apartments, and unresolved candidates are
reported instead of being guessed. If no reference is available, omit it; all
PDF extraction and validation stages still run.

Key outputs include `diagnostics.json`, both page SVGs and previews,
`validation.json`, `page_01_apartment_seeds.json`, and
`page_01/apartment_test_01.svg` (when a usable seed exists).

## Running real validation in GitHub Actions

Open the repository's **Actions** tab, select **Page 01 Validation**, choose
**Run workflow**, and wait for the job to finish. Download the
`interlab-page01-validation` artifact and review `run_summary.md`,
`validation/page_01_reference_alignment_overlay.png`,
`page_01/apartment_test_01.png`, and `page_01_normalized.svg`. The workflow
uses the checked-in `input/Floorplan.pdf` and discovers `01.png` by basename
inside `input/Планировки.zip`; generated files remain Actions artifacts and
are not committed.
