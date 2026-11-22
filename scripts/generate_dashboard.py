#!/usr/bin/env python3
"""
Generate an interactive HTML dashboard from comparison_summary.xlsx.

Includes sample distribution histograms for vector descriptors and
separates unimplemented C++ descriptors into a muted section.

Usage:
    python scripts/generate_dashboard.py
    python scripts/generate_dashboard.py --input data/comparison_analysis/11182026_2120/comparison_summary.xlsx
    python scripts/generate_dashboard.py --out dashboard.html
    python scripts/generate_dashboard.py --no-histograms   # skip histogram generation (faster)
"""

from __future__ import annotations

import argparse
import base64
import html as html_mod
import io
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.comparison import load_matlab_excel, load_cpp_json
from core.mappings import DESCRIPTORS

# Suppress matplotlib/seaborn warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_latest_comparison() -> Path:
    analysis_dir = PROJECT_ROOT / "data" / "comparison_analysis"
    if not analysis_dir.exists():
        raise FileNotFoundError(f"No comparison_analysis directory: {analysis_dir}")
    dirs = sorted(analysis_dir.iterdir(), key=lambda d: d.stat().st_mtime)
    for d in reversed(dirs):
        xlsx = d / "comparison_summary.xlsx"
        if xlsx.exists():
            return xlsx
    raise FileNotFoundError("No comparison_summary.xlsx found")


def pct_color(pct: float) -> str:
    if pct >= 95: return "#16a34a"
    if pct >= 80: return "#65a30d"
    if pct >= 60: return "#ca8a04"
    if pct >= 40: return "#ea580c"
    if pct >= 10: return "#dc2626"
    return "#991b1b"


def fmt(val, decimals=2) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "\u2014"
    if isinstance(val, float):
        if abs(val) < 0.001 and val != 0:
            return f"{val:.2e}"
        return f"{val:.{decimals}f}"
    return str(val)


# ---------------------------------------------------------------------------
# Identify unimplemented descriptors
# ---------------------------------------------------------------------------

def find_unimplemented(scalar_df: pd.DataFrame, vector_df: pd.DataFrame, desc_summary: pd.DataFrame) -> set[str]:
    """Return set of descriptor names that C++ hasn't implemented."""
    unimplemented = set()
    for _, row in desc_summary.iterrows():
        desc = row["descriptor"]
        kind = row["kind"]
        if kind == "scalar":
            sub = scalar_df[scalar_df["key"] == desc]
            all_cpp_zero = (sub["cpp_value"].fillna(0) == 0).all()
            any_matlab = (sub["matlab_value"].fillna(0) != 0).any()
            if all_cpp_zero and any_matlab:
                unimplemented.add(desc)
        else:
            sub = vector_df[vector_df["key"] == desc]
            all_cpp_zero = (sub["n_cpp"].fillna(0) == 0).all()
            if all_cpp_zero:
                unimplemented.add(desc)
    return unimplemented


# ---------------------------------------------------------------------------
# Histogram generation
# ---------------------------------------------------------------------------

def _generate_histogram_b64(
    m_vals: np.ndarray,
    c_vals: np.ndarray,
    descriptor_name: str,
    file_id: str,
    label: str,
) -> str | None:
    """Generate an overlaid histogram and return as base64 PNG string."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    a = np.asarray(c_vals, dtype=float)
    b = np.asarray(m_vals, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if a.size == 0 or b.size == 0:
        return None

    combined = np.concatenate([a, b])
    q25, q75 = np.percentile(combined, [25, 75])
    iqr = max(q75 - q25, 1e-9)
    bin_width = 2 * iqr * (len(combined) ** (-1 / 3))
    if bin_width <= 0:
        bins = 40
    else:
        span = combined.max() - combined.min()
        if span == 0:
            bins = 10
        else:
            bins = max(10, min(60, int(np.ceil(span / bin_width))))

    fig, ax = plt.subplots(figsize=(3.5, 2.2), dpi=100)
    ax.hist(a, bins=bins, density=True, alpha=0.5, color="#2563eb", label="C++")
    ax.hist(b, bins=bins, density=True, alpha=0.5, color="#f97316", label="MATLAB")
    ax.set_title(f"{label}", fontsize=8, fontweight="bold", pad=4)
    ax.set_xlabel(descriptor_name, fontsize=7)
    ax.set_ylabel("Density", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.legend(fontsize=6, loc="upper right")
    fig.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def generate_histograms(
    desc_summary: pd.DataFrame,
    vector_df: pd.DataFrame,
    unimplemented: set[str],
    pairs_df: pd.DataFrame,
    matlab_dir: Path,
    cpp_dir: Path,
) -> dict[str, list[tuple[str, str]]]:
    """
    For each implemented vector descriptor, generate 3 sample histograms
    (best/median/worst by KS p-value). Returns {descriptor: [(label, b64_png), ...]}.
    """
    # Build file lookup: id -> (matlab_filename, cpp_filename)
    file_lookup = {}
    for _, r in pairs_df.iterrows():
        fid = r["id"]
        matlab_file = r.get("matlab", "")
        cpp_file = r.get("cpp", "")
        if pd.notna(matlab_file) and pd.notna(cpp_file) and matlab_file and cpp_file:
            file_lookup[fid] = (str(matlab_file), str(cpp_file))

    # For each implemented vector descriptor, pick 3 samples
    sample_plan: dict[str, list[tuple[str, str]]] = {}  # desc -> [(file_id, label), ...]
    all_needed_ids: set[str] = set()

    for _, row in desc_summary.iterrows():
        desc = row["descriptor"]
        if desc in unimplemented or row["kind"] != "vector":
            continue
        sub = vector_df[vector_df["key"] == desc]
        has_data = sub[(sub["n_cpp"].fillna(0) > 0) & (sub["n_matlab"].fillna(0) > 0)]
        has_data = has_data.dropna(subset=["ks_pvalue"])
        # Only pick files we can actually load
        has_data = has_data[has_data["id"].isin(file_lookup)]
        if len(has_data) == 0:
            continue
        sorted_df = has_data.sort_values("ks_pvalue", ascending=False)
        picks = []
        if len(sorted_df) >= 3:
            best = sorted_df.iloc[0]
            worst = sorted_df.iloc[-1]
            mid = sorted_df.iloc[len(sorted_df) // 2]
            picks = [
                (best["id"], f"Good match (p={best['ks_pvalue']:.3f})"),
                (mid["id"], f"Typical (p={mid['ks_pvalue']:.3f})"),
                (worst["id"], f"Poor match (p={worst['ks_pvalue']:.2e})"),
            ]
        else:
            for i, (_, r) in enumerate(sorted_df.iterrows()):
                picks.append((r["id"], f"Sample {i+1} (p={r['ks_pvalue']:.3f})"))
        sample_plan[desc] = picks
        for fid, _ in picks:
            all_needed_ids.add(fid)

    # Load all needed file data (cached)
    print(f"  Loading {len(all_needed_ids)} scaffold pairs for histograms ...")
    data_cache: dict[str, tuple[dict, dict]] = {}
    for fid in sorted(all_needed_ids):
        if fid not in file_lookup:
            continue
        matlab_file, cpp_file = file_lookup[fid]
        matlab_path = matlab_dir / matlab_file
        cpp_path = cpp_dir / cpp_file
        if not matlab_path.exists() or not cpp_path.exists():
            continue
        try:
            m_data = load_matlab_excel(matlab_path)
            c_data = load_cpp_json(cpp_path, interior_only=True)
            data_cache[fid] = (m_data, c_data)
        except Exception as exc:
            print(f"    [WARN] Failed loading {fid}: {exc}")

    # Generate histograms
    print(f"  Generating histograms for {len(sample_plan)} descriptors ...")
    histograms: dict[str, list[tuple[str, str]]] = {}
    desc_spec_map = DESCRIPTORS  # already keyed by descriptor key

    for desc, picks in sample_plan.items():
        spec = desc_spec_map.get(desc)
        if spec is None:
            continue
        images = []
        for fid, label in picks:
            if fid not in data_cache:
                continue
            m_data, c_data = data_cache[fid]
            m_block = m_data.get(spec.group, {})
            c_block = c_data.get(spec.group, {})
            m_vals = m_block.get(spec.matlab_name)
            c_vals = c_block.get(spec.cpp_name)
            if m_vals is None or c_vals is None:
                continue
            c_vals = np.asarray(c_vals, dtype=float) / spec.cpp_divisor
            m_vals = np.asarray(m_vals, dtype=float)
            b64 = _generate_histogram_b64(m_vals, c_vals, desc, fid, label)
            if b64:
                images.append((label, b64))
        if images:
            histograms[desc] = images

    print(f"  Generated {sum(len(v) for v in histograms.values())} histogram images")
    return histograms


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def build_dashboard(
    input_xlsx: Path,
    pairs_csv: Path | None,
    output_html: Path,
    matlab_dir: Path | None,
    cpp_dir: Path | None,
    gen_histograms: bool = True,
) -> None:
    print(f"Reading {input_xlsx} ...")
    desc_summary = pd.read_excel(input_xlsx, sheet_name="descriptor_summary")
    scalar_df = pd.read_excel(input_xlsx, sheet_name="scalar_descriptors")
    vector_df = pd.read_excel(input_xlsx, sheet_name="vector_descriptors")

    # Load category info
    pairs_df = None
    category_map = {}
    if pairs_csv and pairs_csv.exists():
        pairs_df = pd.read_csv(pairs_csv)
        category_map = pairs_df.set_index("id")["category"].to_dict()

    scalar_df["category"] = scalar_df["id"].map(category_map).fillna("unknown")
    vector_df["category"] = vector_df["id"].map(category_map).fillna("unknown")

    # Identify unimplemented
    unimplemented = find_unimplemented(scalar_df, vector_df, desc_summary)
    impl_summary = desc_summary[~desc_summary["descriptor"].isin(unimplemented)].copy()
    unimpl_summary = desc_summary[desc_summary["descriptor"].isin(unimplemented)].copy()

    n_files = scalar_df["id"].nunique()
    n_total = len(desc_summary)
    n_implemented = len(impl_summary)
    n_unimplemented = len(unimpl_summary)

    # Overall similarity (excluding unimplemented)
    impl_scalar = scalar_df[~scalar_df["key"].isin(unimplemented)]
    impl_vector = vector_df[~vector_df["key"].isin(unimplemented)]
    all_similar = pd.concat([impl_scalar["similar"], impl_vector["similar"]])
    overall_pct = all_similar.mean() * 100 if len(all_similar) > 0 else 0

    # Tier breakdown (implemented only)
    tier_defs = [
        ("Excellent (\u226595%)", 95, 101, "#16a34a", "#dcfce7"),
        ("Good (80\u201395%)", 80, 95, "#65a30d", "#ecfccb"),
        ("Fair (60\u201380%)", 60, 80, "#ca8a04", "#fef9c3"),
        ("Poor (40\u201360%)", 40, 60, "#ea580c", "#ffedd5"),
        ("Bad (<40%)", 0.1, 40, "#dc2626", "#fee2e2"),
        ("No Match (0%)", -0.1, 0.1, "#991b1b", "#fecaca"),
    ]
    tiers = []
    for name, lo, hi, tc, tbg in tier_defs:
        members = impl_summary[(impl_summary["pct_similar"] >= lo) & (impl_summary["pct_similar"] < hi)]
        tiers.append((name, members, tc, tbg))

    # Generate histograms
    histograms: dict[str, list[tuple[str, str]]] = {}
    if gen_histograms and pairs_df is not None and matlab_dir and cpp_dir:
        print("Generating sample histograms ...")
        histograms = generate_histograms(
            desc_summary, vector_df, unimplemented, pairs_df, matlab_dir, cpp_dir,
        )

    # Category breakdown (implemented only)
    cat_scalar = impl_scalar.groupby("category").agg(
        n_files=("id", "nunique"), n_similar=("similar", "sum"), n_total=("similar", "count"),
    ).reset_index()
    cat_scalar["pct"] = (cat_scalar["n_similar"] / cat_scalar["n_total"] * 100).round(1)

    cat_vector = impl_vector.groupby("category").agg(
        n_files=("id", "nunique"), n_similar=("similar", "sum"), n_total=("similar", "count"),
    ).reset_index()
    cat_vector["pct"] = (cat_vector["n_similar"] / cat_vector["n_total"] * 100).round(1)

    # --- Build dissimilar details JSON ---
    dissimilar_details = {}
    for _, row in impl_summary.iterrows():
        desc = row["descriptor"]
        kind = row["kind"]
        df = scalar_df if kind == "scalar" else vector_df
        sub = df[df["key"] == desc]
        dissim = sub[sub["similar"] == False].copy()
        if len(dissim) == 0:
            continue
        details = []
        for _, r in dissim.iterrows():
            d = {"id": r["id"], "category": r.get("category", "")}
            if kind == "scalar":
                d["matlab"] = fmt(r.get("matlab_value"))
                d["cpp"] = fmt(r.get("cpp_value"))
                d["rel_diff"] = fmt(r.get("rel_diff"), 4)
            else:
                d["n_matlab"] = int(r.get("n_matlab", 0)) if not pd.isna(r.get("n_matlab", 0)) else 0
                d["n_cpp"] = int(r.get("n_cpp", 0)) if not pd.isna(r.get("n_cpp", 0)) else 0
                d["ks_stat"] = fmt(r.get("ks_stat"), 4)
                d["wasserstein"] = fmt(r.get("wasserstein"), 4)
            details.append(d)
        dissimilar_details[desc] = details

    details_json = json.dumps(dissimilar_details, default=str)

    # --- Build histogram JSON (descriptor -> [{label, src}]) ---
    hist_json_data = {}
    for desc, images in histograms.items():
        hist_json_data[desc] = [{"label": lbl, "src": f"data:image/png;base64,{b64}"} for lbl, b64 in images]
    hist_json = json.dumps(hist_json_data)

    # --- Build descriptor table rows (implemented only) ---
    desc_rows = []
    for _, row in impl_summary.iterrows():
        pct = row["pct_similar"]
        n_sim = int(row["n_similar"])
        n_tested = int(row["n_files_tested"])
        desc = row["descriptor"]
        kind = row["kind"]
        color = pct_color(pct)

        if kind == "scalar":
            metric = f"Med. Rel Diff: {fmt(row.get('median_rel_diff'), 4)}"
        else:
            metric = f"Med. KS p-val: {fmt(row.get('median_ks_pvalue'), 4)}"

        has_expand = desc in dissimilar_details or desc in histograms
        expand_attr = f'onclick="toggleDetails(\'{html_mod.escape(desc, quote=True)}\')" style="cursor:pointer"' if has_expand else ""
        arrow = '<span class="arrow">&#9654;</span>' if has_expand else '<span class="arrow" style="visibility:hidden">&#9654;</span>'

        desc_rows.append(f"""
        <tr class="desc-row" data-pct="{pct}" data-kind="{kind}" {expand_attr}>
            <td>{arrow} <strong>{html_mod.escape(desc)}</strong></td>
            <td><span class="badge badge-{kind}">{kind}</span></td>
            <td style="text-align:center">
                <div class="pct-bar-container">
                    <div class="pct-bar" style="width:{pct}%;background:{color}"></div>
                </div>
                <span style="color:{color};font-weight:600">{pct:.1f}%</span>
            </td>
            <td style="text-align:center">{n_sim} / {n_tested}</td>
            <td style="text-align:center">{metric}</td>
        </tr>
        <tr class="detail-row" id="detail-{html_mod.escape(desc)}" style="display:none">
            <td colspan="5"><div class="detail-content" id="detail-content-{html_mod.escape(desc)}"></div></td>
        </tr>""")

    # --- Tier cards ---
    tier_cards = []
    for name, members, tc, tbg in tiers:
        count = len(members)
        if count == 0:
            continue
        names_list = members["descriptor"].tolist()
        names = ", ".join(names_list) if count <= 10 else ", ".join(names_list[:8]) + f" +{count-8} more"
        tier_cards.append(f"""
        <div class="tier-card" style="border-left:4px solid {tc};background:{tbg}">
            <div class="tier-header">
                <span class="tier-name" style="color:{tc}">{name}</span>
                <span class="tier-count" style="color:{tc}">{count}</span>
            </div>
            <div class="tier-descriptors">{html_mod.escape(names)}</div>
        </div>""")

    # --- Category rows ---
    cat_rows = []
    for _, r in cat_scalar.sort_values("pct", ascending=False).iterrows():
        cat = r["category"]
        vec_row = cat_vector[cat_vector["category"] == cat]
        vec_pct = vec_row["pct"].values[0] if len(vec_row) > 0 else 0
        scalar_pct = r["pct"]
        cat_rows.append(f"""
        <tr>
            <td><strong>{html_mod.escape(cat)}</strong></td>
            <td style="text-align:center">{int(r['n_files'])}</td>
            <td style="text-align:center">
                <div class="pct-bar-container"><div class="pct-bar" style="width:{scalar_pct}%;background:{pct_color(scalar_pct)}"></div></div>
                <span style="color:{pct_color(scalar_pct)};font-weight:600">{scalar_pct:.1f}%</span>
            </td>
            <td style="text-align:center">
                <div class="pct-bar-container"><div class="pct-bar" style="width:{vec_pct}%;background:{pct_color(vec_pct)}"></div></div>
                <span style="color:{pct_color(vec_pct)};font-weight:600">{vec_pct:.1f}%</span>
            </td>
        </tr>""")

    # --- Unimplemented descriptors list ---
    unimpl_items = []
    for _, row in unimpl_summary.iterrows():
        desc = row["descriptor"]
        kind = row["kind"]
        unimpl_items.append(f'<span class="unimpl-chip"><span class="badge badge-{kind}">{kind}</span> {html_mod.escape(desc)}</span>')

    # --- Excellent count for summary cards ---
    n_excellent = len(tiers[0][1])  # first tier is Excellent
    n_no_match_impl = len([t for t in tiers if "0%" in t[0] and len(t[1]) > 0])
    n_no_match_count = sum(len(t[1]) for t in tiers if "0%" in t[0])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LOVAMAP Comparison Dashboard</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.5; }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 4px; }}
    .subtitle {{ color: #64748b; margin-bottom: 24px; font-size: 0.9rem; }}

    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 16px; margin-bottom: 32px; }}
    .summary-card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
    .summary-card .value {{ font-size: 2rem; font-weight: 700; }}
    .summary-card .label {{ font-size: 0.78rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }}

    .tier-section {{ margin-bottom: 32px; }}
    .tier-card {{ background: white; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
    .tier-header {{ display: flex; justify-content: space-between; align-items: center; }}
    .tier-name {{ font-weight: 700; font-size: 0.95rem; }}
    .tier-count {{ font-weight: 600; font-size: 0.85rem; }}
    .tier-descriptors {{ font-size: 0.82rem; color: #475569; margin-top: 4px; }}

    .section-header {{ font-size: 1.3rem; font-weight: 700; margin: 32px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; }}

    .filter-bar {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }}
    .filter-bar label {{ font-size: 0.85rem; font-weight: 600; color: #475569; }}
    .filter-bar select, .filter-bar input {{ padding: 6px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.85rem; background: white; }}

    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    th {{ background: #f1f5f9; padding: 12px 16px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: #475569; }}
    td {{ padding: 10px 16px; border-top: 1px solid #f1f5f9; font-size: 0.9rem; }}
    tr.desc-row:hover {{ background: #f8fafc; }}

    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }}
    .badge-scalar {{ background: #dbeafe; color: #1d4ed8; }}
    .badge-vector {{ background: #f3e8ff; color: #7c3aed; }}

    .pct-bar-container {{ width: 100%; height: 6px; background: #e2e8f0; border-radius: 3px; margin-bottom: 2px; }}
    .pct-bar {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}

    .arrow {{ display: inline-block; font-size: 0.7rem; transition: transform 0.2s; margin-right: 4px; color: #94a3b8; }}
    .arrow.open {{ transform: rotate(90deg); }}

    .detail-row td {{ padding: 0; background: #f8fafc; }}
    .detail-content {{ padding: 16px 24px; max-height: 600px; overflow-y: auto; }}
    .detail-table {{ width: 100%; font-size: 0.82rem; box-shadow: none; }}
    .detail-table th {{ padding: 6px 10px; font-size: 0.75rem; }}
    .detail-table td {{ padding: 6px 10px; font-size: 0.82rem; border-top: 1px solid #e2e8f0; }}
    .detail-table tr:hover {{ background: #f1f5f9; }}
    .detail-count {{ font-size: 0.82rem; color: #64748b; margin-bottom: 8px; }}

    .hist-grid {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }}
    .hist-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }}
    .hist-card img {{ display: block; max-width: 100%; height: auto; }}

    .cat-table td {{ font-size: 0.9rem; }}

    /* Unimplemented section */
    .unimpl-section {{ background: #f1f5f9; border-radius: 12px; padding: 20px; margin-top: 16px; border: 1px dashed #cbd5e1; }}
    .unimpl-header {{ font-size: 1.1rem; font-weight: 700; color: #94a3b8; margin-bottom: 8px; }}
    .unimpl-note {{ font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; }}
    .unimpl-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .unimpl-chip {{ display: inline-flex; align-items: center; gap: 4px; background: white; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 10px; font-size: 0.82rem; color: #94a3b8; }}
    .unimpl-chip .badge {{ opacity: 0.5; }}

    .tab-bar {{ display: flex; gap: 4px; margin-bottom: 12px; }}
    .tab-btn {{ padding: 4px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background: white; font-size: 0.82rem; cursor: pointer; color: #475569; }}
    .tab-btn.active {{ background: #1e293b; color: white; border-color: #1e293b; }}
</style>
</head>
<body>
<div class="container">

<h1>LOVAMAP Comparison Dashboard</h1>
<p class="subtitle">MATLAB vs C++ descriptor comparison &mdash; {n_files} scaffold pairs &mdash; {n_implemented} implemented descriptors compared (+ {n_unimplemented} not yet in C++)</p>

<div class="summary-grid">
    <div class="summary-card">
        <div class="value">{n_files}</div>
        <div class="label">Scaffold Pairs</div>
    </div>
    <div class="summary-card">
        <div class="value">{n_implemented}</div>
        <div class="label">Descriptors Compared</div>
    </div>
    <div class="summary-card">
        <div class="value" style="color:{pct_color(overall_pct)}">{overall_pct:.1f}%</div>
        <div class="label">Overall Similarity</div>
    </div>
    <div class="summary-card">
        <div class="value" style="color:#16a34a">{n_excellent}</div>
        <div class="label">Excellent (&ge;95%)</div>
    </div>
    <div class="summary-card">
        <div class="value" style="color:#991b1b">{n_no_match_count}</div>
        <div class="label">No Match (0%)</div>
    </div>
    <div class="summary-card">
        <div class="value" style="color:#94a3b8">{n_unimplemented}</div>
        <div class="label">Not in C++ Yet</div>
    </div>
</div>

<div class="section-header">Descriptor Tiers</div>
<div class="tier-section">
    {"".join(tier_cards)}
</div>

<div class="section-header">By Scaffold Category</div>
<p style="font-size:0.82rem;color:#64748b;margin-bottom:8px">Similarity computed only over implemented descriptors</p>
<table class="cat-table">
<thead>
    <tr><th>Category</th><th style="text-align:center">Files</th><th style="text-align:center">Scalar Similarity</th><th style="text-align:center">Vector Similarity</th></tr>
</thead>
<tbody>
    {"".join(cat_rows)}
</tbody>
</table>

<div class="section-header">All Implemented Descriptors</div>
<div class="filter-bar">
    <label>Filter:</label>
    <select id="kindFilter" onchange="filterTable()">
        <option value="all">All types</option>
        <option value="scalar">Scalar only</option>
        <option value="vector">Vector only</option>
    </select>
    <select id="tierFilter" onchange="filterTable()">
        <option value="all">All tiers</option>
        <option value="95">Excellent (&ge;95%)</option>
        <option value="80">Good (80-95%)</option>
        <option value="60">Fair (60-80%)</option>
        <option value="40">Poor (40-60%)</option>
        <option value="10">Bad (&lt;40%)</option>
        <option value="0">No Match (0%)</option>
    </select>
    <input type="text" id="searchInput" placeholder="Search descriptor..." oninput="filterTable()">
</div>
<table id="descriptorTable">
<thead>
    <tr><th>Descriptor</th><th>Type</th><th style="text-align:center">Similarity</th><th style="text-align:center">Similar / Total</th><th style="text-align:center">Key Metric</th></tr>
</thead>
<tbody>
    {"".join(desc_rows)}
</tbody>
</table>

<div class="section-header" style="color:#94a3b8;border-color:#e2e8f0">Not Yet Implemented in C++</div>
<div class="unimpl-section">
    <div class="unimpl-note">These {n_unimplemented} descriptors exist in MATLAB but C++ returns empty/zero for all {n_files} scaffolds. They are excluded from all similarity calculations above.</div>
    <div class="unimpl-list">
        {"".join(unimpl_items)}
    </div>
</div>

</div>

<script>
const dissimilarDetails = {details_json};
const histogramData = {hist_json};

function toggleDetails(desc) {{
    const row = document.getElementById('detail-' + desc);
    const contentDiv = document.getElementById('detail-content-' + desc);
    const arrow = row.previousElementSibling.querySelector('.arrow');

    if (row.style.display === 'none') {{
        row.style.display = '';
        arrow.classList.add('open');

        if (!contentDiv.innerHTML) {{
            let html = '';

            // Histograms
            const hists = histogramData[desc];
            if (hists && hists.length > 0) {{
                html += '<div style="font-size:0.82rem;color:#475569;font-weight:600;margin-bottom:8px">Sample distributions (C++ blue, MATLAB orange)</div>';
                html += '<div class="hist-grid">';
                for (const h of hists) {{
                    html += '<div class="hist-card"><img src="' + h.src + '" alt="' + h.label + '"></div>';
                }}
                html += '</div>';
            }}

            // Dissimilar files table
            const details = dissimilarDetails[desc];
            if (details && details.length > 0) {{
                const isScalar = 'matlab' in details[0];

                // Tab bar: show first 20 / all
                const showAll = details.length <= 30;
                const displayDetails = showAll ? details : details.slice(0, 20);
                html += '<div class="detail-count">' + details.length + ' dissimilar file(s)' + (showAll ? '' : ' &mdash; showing first 20') + '</div>';

                html += '<table class="detail-table"><thead><tr><th>File ID</th><th>Category</th>';
                if (isScalar) {{
                    html += '<th>MATLAB</th><th>C++</th><th>Rel Diff</th>';
                }} else {{
                    html += '<th>n MATLAB</th><th>n C++</th><th>KS Stat</th><th>Wasserstein</th>';
                }}
                html += '</tr></thead><tbody>';
                for (const d of displayDetails) {{
                    html += '<tr><td>' + d.id + '</td><td>' + d.category + '</td>';
                    if (isScalar) {{
                        html += '<td>' + d.matlab + '</td><td>' + d.cpp + '</td><td>' + d.rel_diff + '</td>';
                    }} else {{
                        html += '<td>' + d.n_matlab + '</td><td>' + d.n_cpp + '</td><td>' + d.ks_stat + '</td><td>' + d.wasserstein + '</td>';
                    }}
                    html += '</tr>';
                }}
                html += '</tbody></table>';

                if (!showAll) {{
                    html += '<div id="remaining-' + desc + '" style="display:none"></div>';
                    html += '<button onclick="showAll(\\\'' + desc + '\\\')" style="margin-top:8px;padding:4px 12px;border:1px solid #cbd5e1;border-radius:6px;background:white;font-size:0.82rem;cursor:pointer">Show all ' + details.length + ' files</button>';
                }}
            }}

            contentDiv.innerHTML = html;
        }}
    }} else {{
        row.style.display = 'none';
        arrow.classList.remove('open');
    }}
}}

function showAll(desc) {{
    const details = dissimilarDetails[desc];
    if (!details) return;
    const isScalar = 'matlab' in details[0];
    const contentDiv = document.getElementById('detail-content-' + desc);
    // Rebuild table with all entries
    const tables = contentDiv.querySelectorAll('.detail-table');
    if (tables.length === 0) return;
    const tbody = tables[tables.length - 1].querySelector('tbody');
    tbody.innerHTML = '';
    for (const d of details) {{
        let row = '<tr><td>' + d.id + '</td><td>' + d.category + '</td>';
        if (isScalar) {{
            row += '<td>' + d.matlab + '</td><td>' + d.cpp + '</td><td>' + d.rel_diff + '</td>';
        }} else {{
            row += '<td>' + d.n_matlab + '</td><td>' + d.n_cpp + '</td><td>' + d.ks_stat + '</td><td>' + d.wasserstein + '</td>';
        }}
        row += '</tr>';
        tbody.innerHTML += row;
    }}
    // Update count and remove button
    const countDiv = contentDiv.querySelector('.detail-count');
    if (countDiv) countDiv.textContent = details.length + ' dissimilar file(s)';
    const btn = contentDiv.querySelector('button');
    if (btn) btn.remove();
}}

function filterTable() {{
    const kind = document.getElementById('kindFilter').value;
    const tier = document.getElementById('tierFilter').value;
    const search = document.getElementById('searchInput').value.toLowerCase();
    const rows = document.querySelectorAll('#descriptorTable tbody tr.desc-row');

    rows.forEach(row => {{
        const descName = row.querySelector('td strong').textContent.toLowerCase();
        const rowKind = row.dataset.kind;
        const pct = parseFloat(row.dataset.pct);
        const detailRow = row.nextElementSibling;

        let show = true;
        if (kind !== 'all' && rowKind !== kind) show = false;
        if (search && !descName.includes(search)) show = false;
        if (tier !== 'all') {{
            const t = parseFloat(tier);
            if (t === 0 && pct > 0.05) show = false;
            else if (t === 10 && (pct < 0.1 || pct >= 40)) show = false;
            else if (t === 40 && (pct < 40 || pct >= 60)) show = false;
            else if (t === 60 && (pct < 60 || pct >= 80)) show = false;
            else if (t === 80 && (pct < 80 || pct >= 95)) show = false;
            else if (t === 95 && pct < 95) show = false;
        }}

        row.style.display = show ? '' : 'none';
        if (detailRow && detailRow.classList.contains('detail-row')) {{
            if (!show) detailRow.style.display = 'none';
        }}
    }});
}}
</script>
</body>
</html>
"""

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html_content)
    print(f"Dashboard written to {output_html}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate comparison HTML dashboard.")
    parser.add_argument("--input", type=str, default=None, help="Path to comparison_summary.xlsx")
    parser.add_argument("--pairs", type=str, default=None, help="Path to file_pairs CSV")
    parser.add_argument("--matlab-dir", type=str, default=None, help="Directory with MATLAB xlsx files")
    parser.add_argument("--cpp-dir", type=str, default=None, help="Directory with C++ JSON files")
    parser.add_argument("--out", type=str, default=None, help="Output HTML path")
    parser.add_argument("--no-histograms", action="store_true", help="Skip histogram generation (faster)")
    args = parser.parse_args()

    if args.input:
        input_xlsx = Path(args.input)
    else:
        input_xlsx = find_latest_comparison()

    if args.pairs:
        pairs_csv = Path(args.pairs)
    else:
        pairs_csv = PROJECT_ROOT / "file_pairs_all.csv"
        if not pairs_csv.exists():
            pairs_csv = PROJECT_ROOT / "file_pairs.csv"

    # Try to auto-detect matlab/cpp dirs from the pairs CSV
    matlab_dir = Path(args.matlab_dir) if args.matlab_dir else None
    cpp_dir = Path(args.cpp_dir) if args.cpp_dir else None

    if matlab_dir is None:
        candidate = PROJECT_ROOT / "data" / "descriptors" / "matlab" / "batch_all_scaffolds"
        if candidate.exists():
            matlab_dir = candidate
        else:
            candidate = PROJECT_ROOT / "data" / "descriptors" / "matlab"
            if candidate.exists():
                matlab_dir = candidate

    if cpp_dir is None:
        # Find latest batch_all_* directory
        cpp_base = PROJECT_ROOT / "data" / "descriptors" / "cpp"
        if cpp_base.exists():
            candidates = sorted(cpp_base.glob("batch_all_*"), key=lambda d: d.stat().st_mtime)
            if candidates:
                cpp_dir = candidates[-1]
            else:
                candidates = sorted(cpp_base.glob("batch_*"), key=lambda d: d.stat().st_mtime)
                if candidates:
                    cpp_dir = candidates[-1]

    output_html = Path(args.out) if args.out else input_xlsx.parent / "dashboard.html"

    build_dashboard(
        input_xlsx, pairs_csv, output_html,
        matlab_dir, cpp_dir,
        gen_histograms=not args.no_histograms,
    )


if __name__ == "__main__":
    main()
