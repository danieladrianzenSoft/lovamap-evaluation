"""Config package exports for backward compatibility.

This module re-exports the comparison workflow `ComparisonConfig` and
`load_comparison_config` under the legacy names `Config` and `load_config`,
so existing imports like `from config import Config` continue to work.
It also exposes the data-cleaning and submission config loaders.
"""

from .comparison import ComparisonConfig, load_comparison_config
from .data_cleaning import CleanConfig, load_cleaning_config
from .submission import SubmissionConfig, load_submission_config

# Backwards-compatible names expected by existing code
Config = ComparisonConfig
load_config = load_comparison_config

__all__ = [
	"Config",
	"load_config",
	"CleanConfig",
	"load_cleaning_config",
	"SubmissionConfig",
	"load_submission_config",
]
