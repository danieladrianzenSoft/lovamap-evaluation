"""
Configuration for the data cleaning workflow.

Provides `CleanConfig` and `load_cleaning_config` to configure input/output
directories and filtering parameters for the data cleaning workflow.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CleanConfig:
    raw_dir: Path
    clean_dir: Path
    x_max: float
    y_max: float
    z_max: float
    verbose: bool


# Default values
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "scaffolds" / "raw"
DEFAULT_CLEAN_DIR = PROJECT_ROOT / "data" / "scaffolds" / "clean"
DEFAULT_X_MAX = None
DEFAULT_Y_MAX = None
DEFAULT_Z_MAX = 600
DEFAULT_VERBOSE = True

def load_cleaning_config(
    raw_dir: str | Path | None = None,
    clean_dir: str | Path | None = None,
    x_max: float | None = None,
    y_max: float | None = None,
    z_max: float | None = None,
    verbose: bool | None = None,
) -> CleanConfig:
    raw_dir_path = Path(raw_dir) if raw_dir else DEFAULT_RAW_DIR
    clean_dir_path = Path(clean_dir) if clean_dir else DEFAULT_CLEAN_DIR
    x_max_val = DEFAULT_X_MAX if x_max is None else x_max
    y_max_val = DEFAULT_Y_MAX if y_max is None else y_max
    z_max_val = DEFAULT_Z_MAX if z_max is None else z_max
    verbose_val = DEFAULT_VERBOSE if verbose is None else verbose
    return CleanConfig(
        raw_dir=raw_dir_path,
        clean_dir=clean_dir_path,
        x_max=x_max_val,
        y_max=y_max_val,
        z_max=z_max_val,
        verbose=verbose_val,
    )
