from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

import json
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance

from config import Config
from core.mappings import DESCRIPTORS, DescriptorSpec
from core.comparison_plotting import plot_overlaid_histogram


# ---------- I/O helpers ----------

def load_matlab_excel(path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse MATLAB Excel output into a normalized structure:
      {
        "global": { matlab_header -> scalar },
        "pore":   { matlab_header -> np.ndarray },
        "other":  { matlab_header -> np.ndarray },
      }

    Assumes:
      - Row 0: global descriptor names
      - Row 1: global descriptor values
      - Row 2: per-particle / per-pore descriptor headers
      - Row 3+: data rows
      - Pore descriptors start at the column whose header == "Volume (pL)".
    """
    df = pd.read_excel(path, header=None)

    # --- globals ---
    header_row = df.iloc[0]
    value_row = df.iloc[1]
    global_dict: Dict[str, Any] = {}

    for col_idx, name in header_row.items():
        if isinstance(name, str) and name.strip():
            global_dict[name.strip()] = value_row[col_idx]

    # --- pore / other (vector) descriptors ---
    descriptor_header_row = 2
    headers2 = df.iloc[descriptor_header_row]

    # Find first pore column: "Volume (pL)"
    pore_start_col = None
    for col_idx, name in headers2.items():
        if isinstance(name, str) and name.strip() == "Volume (pL)":
            pore_start_col = col_idx
            break

    pore_descs: Dict[str, np.ndarray] = {}
    other_descs: Dict[str, np.ndarray] = {}

    for col_idx, name in headers2.items():
        if not isinstance(name, str) or not name.strip():
            continue

        # Data rows start at descriptor_header_row + 1 (row 3)
        vals = df.iloc[descriptor_header_row + 1 :, col_idx].dropna().to_numpy()
        if vals.size == 0:
            continue

        # Keep only numeric columns for now (skip UniqueID, etc.)
        try:
            arr = vals.astype(float)
        except ValueError:
            # Non-numeric column -> not used for numeric comparison
            continue

        name_clean = name.strip()
        if pore_start_col is not None and col_idx >= pore_start_col:
            pore_descs[name_clean] = arr
        else:
            other_descs[name_clean] = arr

    return {
        "global": global_dict,
        "pore": pore_descs,
        "other": other_descs,
    }


def load_cpp_json(path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parse LOVAMAP C++ JSON output into:
      {
        "global": { cpp_name -> scalar },
        "pore":   { cpp_name -> np.ndarray },
        "other":  { cpp_name -> np.ndarray },
      }
    """
    with open(path, "r") as f:
        data = json.load(f)

    globals_raw = data.get("globalDescriptors", {})
    globals_norm: Dict[str, Any] = {}
    for k, v in globals_raw.items():
        try:
            globals_norm[k] = float(v)
        except (TypeError, ValueError):
            globals_norm[k] = v  # non-numeric, if any

    def _load_block(block_name: str) -> Dict[str, np.ndarray]:
        out: Dict[str, np.ndarray] = {}
        for name, desc in data.get(block_name, {}).items():
            vals = desc.get("values", [])
            out[name] = np.array(vals, dtype=float)
        return out

    pore_descs = _load_block("poreDescriptors")
    other_descs = _load_block("otherDescriptors")

    return {
        "global": globals_norm,
        "pore": pore_descs,
        "other": other_descs,
    }

# ---------- comparison helpers ----------

def compare_descriptor(
    spec: DescriptorSpec,
    matlab_data: Dict[str, Dict[str, Any]],
    cpp_data: Dict[str, Dict[str, Any]],
    cfg: Config | None = None,
) -> Dict[str, Any]:
    """
    Compare one descriptor (scalar or vector) given its spec and parsed MATLAB/C++ data.

    Returns a dict that always includes:
      - key, group, kind
    And for scalars:
      - matlab_value, cpp_value, abs_diff, rel_diff
    And for vectors:
      - n_matlab, n_cpp, n_overlap, rmse, max_abs_diff
    """
    group = spec.group  # "global" | "pore" | "other"
    kind = spec.kind    # "scalar" | "vector"

    m_block = matlab_data.get(group, {})
    c_block = cpp_data.get(group, {})

    if kind == "scalar":
        if spec.matlab_name not in m_block or spec.cpp_name not in c_block:
            return {
                "key": spec.key,
                "group": group,
                "kind": kind,
                "matlab_present": spec.matlab_name in m_block,
                "cpp_present": spec.cpp_name in c_block,
                "matlab_value": np.nan,
                "cpp_value": np.nan,
                "abs_diff": np.nan,
                "rel_diff": np.nan,
            }

        m_val = float(m_block[spec.matlab_name])
        c_val = float(c_block[spec.cpp_name]/spec.cpp_divisor)
        abs_diff = abs(m_val - c_val)
        rel_diff = abs_diff / max(abs(m_val), 1e-12)

        return {
            "key": spec.key,
            "group": group,
            "kind": kind,
            "matlab_present": True,
            "cpp_present": True,
            "matlab_value": m_val,
            "cpp_value": c_val,
            "abs_diff": abs_diff,
            "rel_diff": rel_diff,
        }

    # kind == "vector"
    if spec.matlab_name not in m_block or spec.cpp_name not in c_block:
        return {
            "key": spec.key,
            "group": group,
            "kind": kind,
            "matlab_present": spec.matlab_name in m_block,
            "cpp_present": spec.cpp_name in c_block,
            "n_matlab": 0,
            "n_cpp": 0,
            "n_overlap": 0,
            "rmse": np.nan,
            "max_abs_diff": np.nan,
            "ks_stat": np.nan,
            "ks_pvalue": np.nan,
            "wasserstein": np.nan,
            "similar": False,
        }

    m_vals = np.asarray(m_block[spec.matlab_name], dtype=float)
    c_vals = np.asarray(c_block[spec.cpp_name]/spec.cpp_divisor, dtype=float)

    m_sorted = np.sort(m_vals)
    c_sorted = np.sort(c_vals)

    n_m = len(m_sorted)
    n_c = len(c_sorted)

    if n_m == 0 or n_c == 0:
        return {
            "key": spec.key,
            "group": group,
            "kind": kind,
            "matlab_present": True,
            "cpp_present": True,
            "n_matlab": n_m,
            "n_cpp": n_c,
            "n_overlap": 0,
            "rmse": np.nan,
            "max_abs_diff": np.nan,
            "ks_stat": np.nan,
            "ks_pvalue": np.nan,
            "wasserstein": np.nan,
            "similar": False,
        }

    n_overlap = min(n_m, n_c)
    diff = m_sorted[:n_overlap] - c_sorted[:n_overlap]
    rmse = float(np.sqrt(np.mean(diff**2)))
    max_abs = float(np.max(np.abs(diff)))

    # Statistical tests on the raw samples
    try:
        ks_res = ks_2samp(m_vals, c_vals)
        ks_stat = float(ks_res.statistic)
        ks_pvalue = float(ks_res.pvalue)
    except Exception:
        ks_stat = np.nan
        ks_pvalue = np.nan

    try:
        wass = float(wasserstein_distance(m_vals, c_vals))
    except Exception:
        wass = np.nan

    # Decide similarity based on thresholds in cfg (fallback defaults)
    ks_thresh = 0.05
    wass_thresh = None
    rmse_thresh = None
    if cfg is not None:
        ks_thresh = getattr(cfg, "ks_pvalue_threshold", ks_thresh)
        wass_thresh = getattr(cfg, "wasserstein_threshold", wass_thresh)
        rmse_thresh = getattr(cfg, "rmse_threshold", rmse_thresh)

    similar = True
    # KS: distributions considered similar if p-value >= threshold
    if not np.isnan(ks_pvalue) and ks_pvalue < ks_thresh:
        similar = False
    # Wasserstein: if threshold provided, require wasserstein <= threshold
    if wass_thresh is not None and not np.isnan(wass):
        if wass > wass_thresh:
            similar = False
    # RMSE: if provided, require rmse <= threshold
    if rmse_thresh is not None and not np.isnan(rmse):
        if rmse > rmse_thresh:
            similar = False

    return {
        "key": spec.key,
        "group": group,
        "kind": kind,
        "matlab_present": True,
        "cpp_present": True,
        "n_matlab": n_m,
        "n_cpp": n_c,
        "n_overlap": n_overlap,
        "rmse": rmse,
        "max_abs_diff": max_abs,
        "ks_stat": ks_stat,
        "ks_pvalue": ks_pvalue,
        "wasserstein": wass,
        "similar": bool(similar),
    }


# ---------- main orchestration ----------

def run_comparison(cfg: Config) -> None:
    """
    High-level pipeline:
      - Load pairs_file (id, matlab, cpp)
      - For each pair:
          * load MATLAB Excel
          * load C++ JSON
          * compare all descriptors in cfg.descriptors_to_compare
      - Write scalar + vector summary sheets to cfg.out_file
    """
    if not cfg.pairs_file.exists():
        print(f"[ERROR] Pairs file not found: {cfg.pairs_file}")
        print("        Create a CSV with columns: id,matlab,cpp")
        return

    pairs_df = pd.read_csv(cfg.pairs_file)

    required_cols = {"id", "matlab", "cpp"}
    missing = required_cols - set(pairs_df.columns)
    if missing:
        print(f"[ERROR] Pairs file {cfg.pairs_file} is missing columns: {missing}")
        return

    scalar_rows: List[Dict[str, Any]] = []
    vector_rows: List[Dict[str, Any]] = []

    for _, row in pairs_df.iterrows():
        test_id = str(row["id"])
        matlab_path = cfg.matlab_dir / str(row["matlab"])
        cpp_path = cfg.cpp_dir / str(row["cpp"])

        print(f"\n--- Comparing {test_id} ---")
        print(f"  MATLAB: {matlab_path}")
        print(f"  C++   : {cpp_path}")

        if not matlab_path.exists():
            print(f"  [WARN] MATLAB file not found: {matlab_path}")
            continue
        if not cpp_path.exists():
            print(f"  [WARN] C++ file not found: {cpp_path}")
            continue

        matlab_data = load_matlab_excel(matlab_path)
        cpp_data = load_cpp_json(cpp_path)

        for key in cfg.descriptors_to_compare:
            spec = DESCRIPTORS.get(key)
            if spec is None:
                print(f"  [WARN] Descriptor key '{key}' not found in DESCRIPTORS registry; skipping.")
                continue

            result = compare_descriptor(spec, matlab_data, cpp_data, cfg)
            result_with_id = {"id": test_id, **result}

            if spec.kind == "scalar":
                scalar_rows.append(result_with_id)
            else:
                vector_rows.append(result_with_id)

            # Simple console feedback
            if spec.kind == "scalar":
                print(
                    f"    {spec.key}: "
                    f"m={result['matlab_value']:.6g}, "
                    f"c={result['cpp_value']:.6g}, "
                    f"rel_err={result['rel_diff']:.3g}"
                )
            else:
                print(
                    f"    {spec.key}: "
                    f"n_m={result['n_matlab']}, n_c={result['n_cpp']}, "
                    f"rmse={result['rmse']:.3g}, "
                    f"max_diff={result['max_abs_diff']:.3g}, "
                    f"ks_p={result.get('ks_pvalue', np.nan):.3g}, "
                    f"wass={result.get('wasserstein', np.nan):.3g}, "
                    f"similar={result.get('similar', False)}"
                )
                # Optionally produce overlaid histogram plots for vector descriptors
                try:
                    if getattr(cfg, "make_plots", False) and spec.key in getattr(cfg, "plot_descriptors", []):
                        # Use matlab filename in plot title and include descriptor key
                        plots_dir = cfg.out_file.parent / "plots"
                        plots_dir.mkdir(parents=True, exist_ok=True)
                        matlab_filename = Path(matlab_path).name
                        plot_xlim = {
                            "PoreVolume": (0.0, 2000.0),
                            "PoreSurfaceArea": (0.0, 2000.0),
                        }
                        # Retrieve arrays again for plotting
                        m_vals = np.asarray(matlab_data.get(spec.group, {}).get(spec.matlab_name, []), dtype=float)
                        c_vals = np.asarray(cpp_data.get(spec.group, {}).get(spec.cpp_name, []), dtype=float)
                        if m_vals.size > 0 and c_vals.size > 0:
                            out_file = plots_dir / f"{test_id}_{spec.key}.png"
                            plot_overlaid_histogram(
                                values_cpp=c_vals,
                                values_matlab=m_vals,
                                out_path=out_file,
                                descriptor_name=spec.key,
                                filename=matlab_filename,
                                xlim=plot_xlim.get(spec.key),
                        )
                except Exception:
                    # plotting must not break the comparison workflow
                    print(f"    [WARN] Plotting failed for {spec.key}")

    # Save summary
    if not scalar_rows and not vector_rows:
        print("\n[INFO] No comparison results to save.")
        return

    scalar_df = pd.DataFrame(scalar_rows) if scalar_rows else pd.DataFrame()
    vector_df = pd.DataFrame(vector_rows) if vector_rows else pd.DataFrame()

    with pd.ExcelWriter(cfg.out_file) as writer:
        if not scalar_df.empty:
            scalar_df.to_excel(writer, sheet_name="scalar_descriptors", index=False)
        if not vector_df.empty:
            vector_df.to_excel(writer, sheet_name="vector_descriptors", index=False)

    print(f"\n[INFO] Comparison summary written to: {cfg.out_file}")
