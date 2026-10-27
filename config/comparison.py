"""
Configuration for the comparison workflow.

Provides a `load_config` function compatible with the previous top-level
`config.py` API.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping
from core.mappings import DESCRIPTORS, validate_descriptor_keys

@dataclass
class ComparisonConfig:
    cpp_dir: Path
    matlab_dir: Path
    pairs_file: Path
    out_file: Path
    make_plots: bool
    plot_descriptors: list[str]
    descriptors_to_compare: list[str]
    cpp_interior_only: bool = True
    # Statistical thresholds for vector comparison
    ks_pvalue_threshold: float = 0.05
    wasserstein_threshold: float | None = None
    rmse_threshold: float | None = None
    # Scalar similarity threshold (relative difference)
    rel_diff_threshold: float = 0.01


# Default values
# PROJECT_ROOT should point to the project root (one level above this config folder)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CPP_BASE = PROJECT_ROOT / "data" / "descriptors" / "cpp"

def _find_latest_batch(base: Path) -> Path:
    """Return the most recently modified batch_* directory, or base itself as fallback."""
    batches = sorted(base.glob("batch_*"), key=lambda p: p.stat().st_mtime)
    return batches[-1] if batches else base
DEFAULT_MATLAB_DIR = PROJECT_ROOT / "data" / "descriptors" / "matlab"
DEFAULT_PAIRS_FILE = PROJECT_ROOT / "file_pairs.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "comparison_analysis"
DEFAULT_OUT_FILE = DEFAULT_OUT_DIR / "comparison_summary.xlsx"
DEFAULT_MAKE_PLOTS = True
DEFAULT_DESCRIPTORS_TO_COMPARE = list(DESCRIPTORS.keys())
DEFAULT_PLOT_DESCRIPTORS = [
    "PoreLongestLength",
    "PoreAspectRatio",
    "PoreLargestEnclosedSphere",
    "PoreAvgInternalDiam"
]


def load_comparison_config(
    cpp_dir: str | Path | None = None,
    matlab_dir: str | Path | None = None,
    pairs_file: str | Path | None = None,
    out_file: str | Path | None = None,
    make_plots: bool | None = None,
    plot_descriptors: list[str] | None = None,
    descriptors_to_compare: list[str] | None = None,
    cpp_interior_only: bool | None = None,
    ks_pvalue_threshold: float | None = None,
    wasserstein_threshold: float | None = None,
    rmse_threshold: float | None = None,
    rel_diff_threshold: float | None = None,
) -> ComparisonConfig:
    cpp_dir_path = Path(cpp_dir) if cpp_dir else _find_latest_batch(DEFAULT_CPP_BASE)
    matlab_dir_path = Path(matlab_dir) if matlab_dir else DEFAULT_MATLAB_DIR
    pairs_file_path = Path(pairs_file) if pairs_file else DEFAULT_PAIRS_FILE
    if out_file:
        out_file_path = Path(out_file)
    else:
        timestamp = datetime.now().strftime("%m%d%Y_%H%M")
        out_file_path = DEFAULT_OUT_DIR / timestamp / "comparison_summary.xlsx"
    make_plots_val = DEFAULT_MAKE_PLOTS if make_plots is None else make_plots
    cpp_interior_only_val = True if cpp_interior_only is None else cpp_interior_only
    ks_pvalue_val = 0.05 if ks_pvalue_threshold is None else ks_pvalue_threshold
    wasserstein_val = None if wasserstein_threshold is None else wasserstein_threshold
    rmse_val = None if rmse_threshold is None else rmse_threshold
    rel_diff_val = 0.01 if rel_diff_threshold is None else rel_diff_threshold

    if descriptors_to_compare is None:
        descriptors_to_compare = DEFAULT_DESCRIPTORS_TO_COMPARE
    if plot_descriptors is None:
        plot_descriptors = DEFAULT_PLOT_DESCRIPTORS
    plot_descriptors_val = validate_descriptor_keys(plot_descriptors)

    return ComparisonConfig(
        cpp_dir=cpp_dir_path,
        matlab_dir=matlab_dir_path,
        pairs_file=pairs_file_path,
        out_file=out_file_path,
        make_plots=make_plots_val,
        plot_descriptors=plot_descriptors_val,
        descriptors_to_compare=descriptors_to_compare,
        cpp_interior_only=cpp_interior_only_val,
        ks_pvalue_threshold=ks_pvalue_val,
        wasserstein_threshold=wasserstein_val,
        rmse_threshold=rmse_val,
        rel_diff_threshold=rel_diff_val,
    )
