"""
Configuration for the comparison workflow.

Provides a `load_config` function compatible with the previous top-level
`config.py` API.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from core.mappings import DESCRIPTORS

@dataclass
class ComparisonConfig:
    cpp_dir: Path
    matlab_dir: Path
    pairs_file: Path
    out_file: Path
    make_plots: bool
    descriptors_to_compare: list[str]
    # Statistical thresholds for vector comparison
    ks_pvalue_threshold: float = 0.05
    wasserstein_threshold: float | None = None
    rmse_threshold: float | None = None


# Default values
# PROJECT_ROOT should point to the project root (one level above this config folder)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# DEFAULT_CPP_DIR = Path("/Users/dzen/Documents/LOVAMAP/LOVAMAP_CPP_TestFiles/Lovamap_Cpp_Outputs")
DEFAULT_CPP_DIR = Path("/Users/dzen/Documents/LOVAMAP/LOVAMAP_Evaluation/data/cpp_output_z600_filtered_v2")
DEFAULT_MATLAB_DIR = Path("/Users/dzen/Documents/LOVAMAP/LOVAMAP_CPP_TestFiles/Lovamap_Matlab_Outputs")
DEFAULT_PAIRS_FILE = PROJECT_ROOT / "file_pairs.csv"
DEFAULT_OUT_FILE = PROJECT_ROOT / "comparison_summary.xlsx"
DEFAULT_MAKE_PLOTS = True
DEFAULT_DESCRIPTORS_TO_COMPARE = list(DESCRIPTORS.keys())


def load_comparison_config(
    cpp_dir: str | Path | None = None,
    matlab_dir: str | Path | None = None,
    pairs_file: str | Path | None = None,
    out_file: str | Path | None = None,
    make_plots: bool | None = None,
    descriptors_to_compare: list[str] | None = None,
    ks_pvalue_threshold: float | None = None,
    wasserstein_threshold: float | None = None,
    rmse_threshold: float | None = None,
) -> ComparisonConfig:
    cpp_dir_path = Path(cpp_dir) if cpp_dir else DEFAULT_CPP_DIR
    matlab_dir_path = Path(matlab_dir) if matlab_dir else DEFAULT_MATLAB_DIR
    pairs_file_path = Path(pairs_file) if pairs_file else DEFAULT_PAIRS_FILE
    out_file_path = Path(out_file) if out_file else DEFAULT_OUT_FILE
    make_plots_val = DEFAULT_MAKE_PLOTS if make_plots is None else make_plots
    ks_pvalue_val = 0.05 if ks_pvalue_threshold is None else ks_pvalue_threshold
    wasserstein_val = None if wasserstein_threshold is None else wasserstein_threshold
    rmse_val = None if rmse_threshold is None else rmse_threshold

    if descriptors_to_compare is None:
        descriptors_to_compare = DEFAULT_DESCRIPTORS_TO_COMPARE

    return ComparisonConfig(
        cpp_dir=cpp_dir_path,
        matlab_dir=matlab_dir_path,
        pairs_file=pairs_file_path,
        out_file=out_file_path,
        make_plots=make_plots_val,
        descriptors_to_compare=descriptors_to_compare,
        ks_pvalue_threshold=ks_pvalue_val,
        wasserstein_threshold=wasserstein_val,
        rmse_threshold=rmse_val,
    )
