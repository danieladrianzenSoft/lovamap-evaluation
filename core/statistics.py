"""Compute summary statistics on LOVAMAP descriptor outputs and export to CSV."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from scipy.stats import gaussian_kde

from core.comparison import load_cpp_json

# Global descriptors to exclude from the statistics CSV
_GLOBAL_EXCLUDES = {"Dx", "DomainSize", "AvgVoidAreaFraction", "NumVoxels"}


# ---------- MATLAB JSON loader ----------

def load_matlab_json(path: Path) -> List[Dict[str, Dict[str, Any]]]:
    """Parse a MATLAB-format JSON file into a list of scaffold dicts.

    Each file may contain multiple scaffolds. Returns a list of dicts,
    each with the same structure as load_cpp_json output:
      {"global": {name: scalar}, "pore": {name: np.ndarray}, "other": {name: np.ndarray}}

    Also returns scaffold identifiers (filename + index).
    """
    with open(path, "r") as f:
        data = json.load(f)

    results: List[Tuple[str, Dict[str, Dict[str, Any]]]] = []
    scaffolds = data.get("scaffolds", [])
    base_name = path.stem

    for idx, scaffold in enumerate(scaffolds):
        # Scaffold name: use filename + index if multiple scaffolds
        if len(scaffolds) == 1:
            scaffold_name = base_name
        else:
            scaffold_name = f"{base_name}_s{idx}"

        # Global descriptors: list of {name, value}
        globals_norm: Dict[str, Any] = {}
        for item in scaffold.get("globalDescriptors", []):
            name = item.get("name", "")
            val = item.get("value")
            if name:
                try:
                    globals_norm[name] = float(val)
                except (TypeError, ValueError):
                    globals_norm[name] = val

        def _parse_values(raw_vals: list) -> np.ndarray:
            """Parse values that may be plain numbers or {id, value} dicts."""
            if not raw_vals:
                return np.array([], dtype=float)
            if isinstance(raw_vals[0], dict):
                return np.array([v["value"] for v in raw_vals], dtype=float)
            return np.array(raw_vals, dtype=float)

        # Pore descriptors: list of {name, values: [{id, value}, ...]}
        pore_descs: Dict[str, np.ndarray] = {}
        for item in scaffold.get("poreDescriptors", []):
            name = item.get("name", "")
            if not name:
                continue
            raw_vals = item.get("values", [])
            if not raw_vals:
                continue
            try:
                pore_descs[name] = _parse_values(raw_vals)
            except (KeyError, TypeError, ValueError):
                continue

        # Other descriptors: list of {name, values: [number, ...]} or {name, values: [{id, value}, ...]}
        other_descs: Dict[str, np.ndarray] = {}
        for item in scaffold.get("otherDescriptors", []):
            name = item.get("name", "")
            if not name:
                continue
            raw_vals = item.get("values", [])
            if not raw_vals:
                continue
            try:
                other_descs[name] = _parse_values(raw_vals)
            except (KeyError, TypeError, ValueError):
                continue

        results.append((scaffold_name, {
            "global": globals_norm,
            "pore": pore_descs,
            "other": other_descs,
        }))

    return results


def compute_vector_stats(arr: np.ndarray) -> Dict[str, float]:
    """Compute summary statistics for a 1-D numeric array.

    Returns dict with: min, q1, median, q3, max, mean, mode, std_error, peak_frequency.
    Mode is estimated via KDE (argmax of density), peak_frequency is the KDE density at mode.
    """
    n = len(arr)
    if n == 0:
        return {k: np.nan for k in ("min", "q1", "median", "q3", "max", "mean", "mode", "std_error", "peak_frequency")}

    stats: Dict[str, float] = {
        "min": float(np.min(arr)),
        "q1": float(np.percentile(arr, 25)),
        "median": float(np.median(arr)),
        "q3": float(np.percentile(arr, 75)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std_error": float(np.std(arr, ddof=1) / np.sqrt(n)) if n > 1 else 0.0,
    }

    # KDE-based mode and peak frequency
    if n >= 2 and np.std(arr) > 0:
        try:
            kde = gaussian_kde(arr)
            x_grid = np.linspace(arr.min(), arr.max(), 1000)
            density = kde(x_grid)
            mode_idx = np.argmax(density)
            stats["mode"] = float(x_grid[mode_idx])
            stats["peak_frequency"] = float(density[mode_idx])
        except Exception:
            stats["mode"] = np.nan
            stats["peak_frequency"] = np.nan
    else:
        # Constant array or single element — mode is the value itself
        stats["mode"] = float(arr[0])
        stats["peak_frequency"] = np.nan

    return stats


def _data_to_stats_row(
    scaffold_name: str,
    data: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Convert a parsed scaffold data dict into a flat statistics row."""
    row: Dict[str, Any] = {"scaffold": scaffold_name}

    # Global descriptors (excluding Dx, DomainSize, AvgVoidAreaFraction, NumVoxels)
    for key, val in data["global"].items():
        if key not in _GLOBAL_EXCLUDES:
            row[key] = val

    # Vector descriptors from both pore and other groups
    stat_keys = ("min", "q1", "median", "q3", "max", "mean", "mode", "std_error", "peak_frequency")

    for group_name in ("pore", "other"):
        for desc_name, arr in data[group_name].items():
            if arr.size == 0:
                continue
            if not np.issubdtype(arr.dtype, np.number):
                continue
            stats = compute_vector_stats(arr)
            for sk in stat_keys:
                row[f"{desc_name}_{sk}"] = stats[sk]

    return row


def run_statistics(
    input_dir: Path,
    output_path: Path,
    interior_only: bool = True,
    source_format: str = "cpp",
) -> Path:
    """Compute statistics for all JSON files in input_dir and write to CSV.

    Args:
        source_format: "cpp" for LOVAMAP C++ JSON output, "matlab" for LOVAMAP MATLAB JSON output.
    """
    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        print(f"[WARN] No JSON files found in {input_dir}")
        return output_path

    rows: List[Dict[str, Any]] = []
    for jf in json_files:
        if source_format == "matlab":
            scaffolds = load_matlab_json(jf)
            for scaffold_name, data in scaffolds:
                print(f"  Processing {scaffold_name} ...")
                rows.append(_data_to_stats_row(scaffold_name, data))
        else:
            print(f"  Processing {jf.name} ...")
            data = load_cpp_json(jf, interior_only=interior_only)
            rows.append(_data_to_stats_row(jf.name, data))

    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n[INFO] Statistics CSV written to: {output_path}")
    print(f"  {len(rows)} scaffolds, {len(df.columns)} columns")
    return output_path


# ---------- Feature reduction via correlation clustering ----------

def _cluster_features(
    corr: pd.DataFrame,
    threshold: float,
) -> Tuple[List[str], List[List[str]]]:
    """Cluster features by Spearman correlation and return singletons + redundant groups.

    Args:
        corr: Spearman correlation matrix (features x features).
        threshold: Minimum |r| to consider features redundant (e.g. 0.95).

    Returns:
        (singletons, redundant_groups) where singletons are independent features
        and redundant_groups are lists of correlated features.
    """
    dist_matrix = 1 - corr.abs()
    dist_matrix = (dist_matrix + dist_matrix.T) / 2
    np.fill_diagonal(dist_matrix.values, 0)
    dist_matrix = dist_matrix.clip(lower=0)

    condensed = squareform(dist_matrix.values)
    Z = linkage(condensed, method="average")

    # distance = 1 - threshold (e.g. threshold=0.95 -> distance=0.05)
    clusters = fcluster(Z, t=1 - threshold, criterion="distance")

    feature_names = corr.columns.tolist()
    cluster_map: Dict[int, List[str]] = defaultdict(list)
    for feat, cid in zip(feature_names, clusters):
        cluster_map[cid].append(feat)

    singletons = []
    redundant_groups = []
    for members in cluster_map.values():
        if len(members) == 1:
            singletons.append(members[0])
        else:
            redundant_groups.append(members)

    return singletons, redundant_groups


def _pick_representatives(
    corr: pd.DataFrame,
    singletons: List[str],
    redundant_groups: List[List[str]],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Pick the most central feature from each redundant cluster.

    Returns:
        (selected_features, cluster_info) where cluster_info is a list of dicts
        with representative, cluster_size, and dropped_features.
    """
    selected = list(singletons)
    cluster_info: List[Dict[str, Any]] = []

    for members in singletons:
        cluster_info.append({
            "representative": members,
            "cluster_size": 1,
            "dropped_features": "",
        })

    for group in redundant_groups:
        sub_corr = corr.loc[group, group].abs()
        mean_corr = sub_corr.mean(axis=1)
        rep = mean_corr.idxmax()
        selected.append(rep)
        dropped = [m for m in group if m != rep]
        cluster_info.append({
            "representative": rep,
            "cluster_size": len(group),
            "dropped_features": "; ".join(dropped),
        })

    return selected, cluster_info


def run_reduce(
    stats_csv: Path,
    output_dir: Path,
    threshold: float = 0.95,
) -> Tuple[Path, Path]:
    """Run correlation-based feature reduction on a statistics CSV.

    Args:
        stats_csv: Path to the full descriptor_statistics.csv.
        output_dir: Directory to write output files.
        threshold: Minimum |Spearman r| to consider features redundant.

    Returns:
        (reduced_csv_path, mapping_csv_path)
    """
    df = pd.read_csv(stats_csv)
    scaffold_col = df["scaffold"]
    df_numeric = df.drop(columns=["scaffold"])

    # Drop constant and all-NaN columns
    df_numeric = df_numeric.dropna(axis=1, how="all")
    df_numeric = df_numeric.loc[:, df_numeric.nunique() > 1]

    print(f"  Features after dropping constant/all-NaN: {df_numeric.shape[1]}")
    print(f"  Samples (scaffolds): {df_numeric.shape[0]}")

    df_filled = df_numeric.fillna(df_numeric.median())
    corr = df_filled.corr(method="spearman")

    singletons, redundant_groups = _cluster_features(corr, threshold)
    selected, cluster_info = _pick_representatives(corr, singletons, redundant_groups)

    n_redundant_features = sum(len(g) for g in redundant_groups)

    print(f"\n  |Spearman r| >= {threshold} threshold:")
    print(f"    Independent features: {len(singletons)}")
    print(f"    Redundant clusters:   {len(redundant_groups)} ({n_redundant_features} features)")
    print(f"    Representative features: {len(selected)}")

    # Print cluster details
    for i, group in enumerate(redundant_groups, 1):
        sub_corr = corr.loc[group, group]
        min_r = sub_corr.where(~np.eye(len(group), dtype=bool)).abs().min().min()
        # Find the representative for this group
        rep = [ci["representative"] for ci in cluster_info if ci["cluster_size"] > 1 and ci["representative"] in group][0]
        dropped = [m for m in group if m != rep]
        print(f"\n    Cluster {i} ({len(group)} features, min |r|={min_r:.3f}):")
        print(f"      Representative: {rep}")
        for d in dropped:
            print(f"      Dropped: {d}")

    # Write reduced CSV (include threshold in filename)
    output_dir.mkdir(parents=True, exist_ok=True)
    thresh_str = str(threshold).replace(".", "")
    reduced_path = output_dir / f"descriptor_statistics_reduced_{thresh_str}.csv"
    out_df = pd.concat([scaffold_col, df[selected]], axis=1)
    out_df.to_csv(reduced_path, index=False)

    # Write cluster mapping
    mapping_path = output_dir / f"feature_cluster_mapping_{thresh_str}.csv"
    mapping_df = pd.DataFrame(cluster_info)
    mapping_df.to_csv(mapping_path, index=False)

    print(f"\n[INFO] Reduced CSV written to: {reduced_path}")
    print(f"  {len(out_df)} scaffolds, {len(selected)} features")
    print(f"[INFO] Cluster mapping written to: {mapping_path}")

    return reduced_path, mapping_path
