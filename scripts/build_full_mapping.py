#!/usr/bin/env python3
"""
Build the full mapping between MATLAB Excel sheets and C++ JSON outputs.

Enumerates all multi-sheet Excel files from the Box data descriptors folder,
extracts each replicate sheet to an individual .xlsx file, matches each to its
C++ JSON counterpart using heuristic naming rules, and generates
``file_pairs_all.csv`` for use with the comparison pipeline.

Usage:
    python scripts/build_full_mapping.py

    # Dry-run (report only, no file extraction):
    python scripts/build_full_mapping.py --dry-run

    # Custom paths:
    python scripts/build_full_mapping.py \
        --box-dir /path/to/lovamap_data_descriptors \
        --cpp-dir /path/to/cpp/batch \
        --out file_pairs_all.csv
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_BOX_DIR = Path(
    "/Users/dzen/Library/CloudStorage/Box-Box/MIMC/lovamap_data_descriptors"
)
DEFAULT_CPP_DIR = PROJECT_ROOT / "data" / "descriptors" / "cpp" / "batch_all_scaffolds"
DEFAULT_MATLAB_OUT_DIR = (
    PROJECT_ROOT / "data" / "descriptors" / "matlab" / "batch_all_scaffolds"
)
DEFAULT_PAIRS_OUT = PROJECT_ROOT / "file_pairs_all.csv"

# Domain folders to include (relative to BOX_DIR).
DOMAIN_FOLDERS = [
    "spheres",
    "ellipsoids",
    "rods",
    "nuggets",
    "hexagonal",
    "square",
    "directionality",
    "normal_distribution",
    "uniform_distribution",
    "semi_soft",
    "soft",
    "stiffness_mixtures",
    "bidisperse",
]

# Sheets to skip when enumerating replicates.
SKIP_SHEETS = {"Cumulative data", "Cumulative Data", "Sheet1"}


# ---------------------------------------------------------------------------
# Step 1 — enumerate sources
# ---------------------------------------------------------------------------

def enumerate_sources(box_dir: Path) -> list[dict]:
    """Walk domain folders and return one record per (Excel file, sheet)."""
    sources: list[dict] = []

    for domain in DOMAIN_FOLDERS:
        domain_path = box_dir / domain
        if not domain_path.exists():
            print(f"  [WARN] Domain folder not found: {domain_path}")
            continue

        for excel_path in sorted(domain_path.rglob("*.xlsx")):
            # Skip temp files, summary-by-descriptor files
            if excel_path.name.startswith("~$"):
                continue
            if "statsbydescrip" in excel_path.name:
                continue

            try:
                xl = pd.ExcelFile(excel_path)
                sheets = [s for s in xl.sheet_names if s not in SKIP_SHEETS]
                xl.close()
            except Exception as exc:
                print(f"  [WARN] Cannot read {excel_path.name}: {exc}")
                continue

            for sheet in sheets:
                sources.append(
                    {
                        "domain": domain,
                        "excel_path": excel_path,
                        "excel_name": excel_path.name,
                        "sheet": sheet,
                    }
                )

    return sources


# ---------------------------------------------------------------------------
# Step 2 — extract individual sheets
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    """Replace filesystem-unsafe characters in a sheet name."""
    return name.replace("/", "_").replace("\\", "_").replace(":", "_")


def extract_sheet(excel_path: Path, sheet: str, out_path: Path) -> None:
    """Extract one sheet to a standalone single-sheet .xlsx file."""
    df = pd.read_excel(excel_path, sheet_name=sheet, header=None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, header=False, index=False)


# ---------------------------------------------------------------------------
# Step 3 — heuristic matching
# ---------------------------------------------------------------------------

def _match_stiffness(sheet: str, excel_name: str, cpp_files: set[str]) -> str | None:
    """Match stiffness_mixtures sheets to C++ files."""
    letter_m = re.search(r"stiffness_mixtures_([a-e])_", excel_name)
    letter = letter_m.group(1) if letter_m else None

    # Letter a: {100,100}_100_{0,100}_N sheets
    if letter == "a" and sheet.startswith("{"):
        c = f"beadInfo_stiffness_mixtures_a_{sheet}.json"
        if c in cpp_files:
            return c

    # Letters b–d: {soft-X.XX,hard-Y.YY}_NN sheets
    m = re.match(r"\{(soft-[\d.]+,hard-[\d.]+)\}_(\d+)", sheet)
    if m:
        ratio, num = m.group(1), m.group(2)
        c = f"labeledDomain_spheres_s{num}.{{{ratio}}}.json"
        if c in cpp_files:
            return c

    # Letter e: FEM_Beads_sN
    if sheet.startswith("FEM_Beads_"):
        suffix = sheet.replace("FEM_Beads_", "")  # e.g. "s1"
        for pattern in [
            f"labeledDomain_FEM_Spheres_stiffness_mixtures_soft_{suffix}.json",
            f"labeledDomain_FEM_Beads_{suffix}.json",
        ]:
            if pattern in cpp_files:
                return pattern

    return None


def _match_semi_soft(sheet: str, cpp_files: set[str]) -> str | None:
    """Match semi_soft sheets to C++ files."""
    # semi_squishy_spheres_50 → labeledDomain_semi-soft-spheres_50.json
    if sheet == "semi_squishy_spheres_50":
        c = "labeledDomain_semi-soft-spheres_50.json"
        return c if c in cpp_files else None

    # semi-soft-spheres_<size>_v<N> → labeledDomain_<sheet>.json
    if sheet.startswith("semi-soft-spheres_"):
        c = f"labeledDomain_{sheet}.json"
        return c if c in cpp_files else None

    # semisoft_<N> (from stats_semi_soft_100_diam) → semi-soft-spheres_100_v<N>
    m = re.match(r"semisoft_(\d+)", sheet)
    if m:
        num = m.group(1)
        c = f"labeledDomain_semi-soft-spheres_100_v{num}.json"
        return c if c in cpp_files else None

    return None


def match_sheet_to_cpp(
    sheet: str, domain: str, excel_name: str, cpp_files: set[str]
) -> str | None:
    """Return the matching C++ JSON filename, or None if unmatched."""

    # --- domain-specific handlers ---
    if domain == "stiffness_mixtures":
        return _match_stiffness(sheet, excel_name, cpp_files)

    if domain == "semi_soft":
        return _match_semi_soft(sheet, cpp_files)

    if domain == "soft":
        # soft_<N> → labeledDomain_soft-spheres_100_v<N>.json
        m = re.match(r"soft_(\d+)", sheet)
        if m:
            num = m.group(1)
            c = f"labeledDomain_soft-spheres_100_v{num}.json"
            return c if c in cpp_files else None
        return None

    # --- sheets starting with '{' (spheres / bidisperse) ---
    if sheet.startswith("{"):
        c = f"beadInfo_spheres_{sheet}.json"
        return c if c in cpp_files else None

    # --- named spheres: spheres_*, beadInfo_<sheet>.json ---
    if sheet.startswith("spheres_"):
        c = f"beadInfo_{sheet}.json"
        return c if c in cpp_files else None

    # --- hexagonal: hex<NNN> ---
    if sheet.startswith("hex"):
        size = sheet[3:]  # e.g. "040"
        for pattern in [
            f"inverse_spheres_hex_{size}.json",
            f"inverse_hex{size}.json",
        ]:
            if pattern in cpp_files:
                return pattern
        return None

    # --- square: square_<NNN> ---
    if sheet.startswith("square_"):
        size = sheet.split("_")[1]
        for pattern in [
            f"beadInfo_spheres_square_{size}.json",
            f"beadInfo_square{int(size)}.json",
            f"beadInfo_square{size}.json",
            f"beadInfo_square_{size}.json",
        ]:
            if pattern in cpp_files:
                return pattern
        return None

    # --- directionality ---
    if sheet.startswith("rbd_ellipsoids_"):
        suffix = sheet.replace("rbd_ellipsoids_", "")
        c = f"labeledDomain_rbd_isotropic_ellipsoids_{suffix}.json"
        return c if c in cpp_files else None

    if sheet == "anisotropic_ellipsoids":
        c = "labeledDomain_anisotropic_ellipsoids.json"
        return c if c in cpp_files else None

    if sheet == "perfectEllipsoids":
        c = "labeledDomain_perfect_ellipsoids.json"
        return c if c in cpp_files else None

    # --- general labeledDomain (ellipsoids, rods, nuggets) ---
    if sheet.startswith(("ellipsoids_", "rods_", "nuggets_")):
        c = f"labeledDomain_{sheet}.json"
        return c if c in cpp_files else None

    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_mapping(
    box_dir: Path,
    cpp_dir: Path,
    matlab_out_dir: Path,
    pairs_out: Path,
    dry_run: bool = False,
) -> None:
    print("=" * 60)
    print("Building Full Scaffold Mapping")
    print("=" * 60)
    print(f"  Box source    : {box_dir}")
    print(f"  C++ dir       : {cpp_dir}")
    print(f"  MATLAB out dir: {matlab_out_dir}")
    print(f"  Pairs CSV     : {pairs_out}")
    print(f"  Dry run       : {dry_run}")
    print()

    # 1 — enumerate
    print("Step 1: Enumerating MATLAB Excel sources ...")
    sources = enumerate_sources(box_dir)
    n_excels = len({s["excel_name"] for s in sources})
    print(f"  Found {len(sources)} sheets across {n_excels} Excel files\n")

    # 2 — enumerate C++ outputs
    print("Step 2: Enumerating C++ JSON outputs ...")
    cpp_files: set[str] = set()
    if cpp_dir.exists():
        cpp_files = {f.name for f in cpp_dir.glob("*.json")}
    print(f"  Found {len(cpp_files)} JSON files\n")

    # 3 — extract & match
    action = "Matching" if dry_run else "Extracting & matching"
    print(f"Step 3: {action} ...")
    matched_cpp: set[str] = set()
    rows: list[dict] = []

    for src in sources:
        sheet = src["sheet"]
        domain = src["domain"]
        excel_name = src["excel_name"]
        excel_path: Path = src["excel_path"]

        safe_sheet = _safe_filename(sheet)
        out_name = f"{domain}__{safe_sheet}.xlsx"
        out_path = matlab_out_dir / out_name

        # Extract
        if not dry_run:
            try:
                extract_sheet(excel_path, sheet, out_path)
            except Exception as exc:
                print(f"  [ERROR] Extract failed for {excel_name} / {sheet}: {exc}")
                continue

        # Match
        cpp_match = match_sheet_to_cpp(sheet, domain, excel_name, cpp_files)
        if cpp_match:
            matched_cpp.add(cpp_match)

        pair_id = f"{domain}__{safe_sheet}"
        rows.append(
            {
                "id": pair_id,
                "matlab": out_name,
                "cpp": cpp_match or "",
                "category": domain,
                "source_excel": excel_name,
                "source_sheet": sheet,
            }
        )

    # 4 — write CSV
    print(f"\nStep 4: Writing {pairs_out} ...")
    df = pd.DataFrame(rows)
    df.to_csv(pairs_out, index=False)
    print(f"  Written {len(df)} rows")

    # 5 — report
    matched = df[df["cpp"] != ""]
    unmatched_matlab = df[df["cpp"] == ""]
    unmatched_cpp = sorted(cpp_files - matched_cpp)

    print()
    print("=" * 60)
    print("MAPPING SUMMARY")
    print("=" * 60)
    print(f"  Total MATLAB sheets : {len(df)}")
    print(f"  Total C++ files     : {len(cpp_files)}")
    print(f"  Matched pairs       : {len(matched)}")
    print(f"  MATLAB-only (no C++): {len(unmatched_matlab)}")
    print(f"  C++-only (no MATLAB): {len(unmatched_cpp)}")
    print()

    print("By category:")
    for cat, grp in sorted(df.groupby("category")):
        n_total = len(grp)
        n_matched = (grp["cpp"] != "").sum()
        print(f"  {cat:30s}: {n_matched:3d} / {n_total:3d} matched")
    print()

    if len(unmatched_matlab) > 0:
        print(f"Unmatched MATLAB sheets ({len(unmatched_matlab)}):")
        for _, row in unmatched_matlab.iterrows():
            print(f"  [{row['category']}] {row['source_sheet']}")
        print()

    if unmatched_cpp:
        print(f"Unmatched C++ files ({len(unmatched_cpp)}):")
        for f in unmatched_cpp:
            print(f"  {f}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build full MATLAB ↔ C++ mapping for the simulated scaffold deck."
    )
    parser.add_argument(
        "--box-dir",
        type=str,
        default=str(DEFAULT_BOX_DIR),
        help="Root of Box lovamap_data_descriptors folder.",
    )
    parser.add_argument(
        "--cpp-dir",
        type=str,
        default=str(DEFAULT_CPP_DIR),
        help="Directory containing C++ JSON outputs.",
    )
    parser.add_argument(
        "--matlab-out-dir",
        type=str,
        default=str(DEFAULT_MATLAB_OUT_DIR),
        help="Directory to write extracted single-sheet .xlsx files.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(DEFAULT_PAIRS_OUT),
        help="Output CSV path (default: file_pairs_all.csv).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report matching only — do not extract sheets.",
    )
    args = parser.parse_args()

    build_mapping(
        box_dir=Path(args.box_dir),
        cpp_dir=Path(args.cpp_dir),
        matlab_out_dir=Path(args.matlab_out_dir),
        pairs_out=Path(args.out),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
