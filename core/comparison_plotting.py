"""Plotting utilities for descriptor comparison.

Provides helpers to create overlaid histograms for vector descriptors
from lovamap-cpp and MATLAB outputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


def plot_overlaid_histogram(
    values_cpp: Sequence[float],
    values_matlab: Sequence[float],
    out_path: Path,
    descriptor_name: str,
    filename: str,
    bins: int | None = None,
    density: bool = True,
    figsize: tuple[int, int] = (8, 5),
    xlim: tuple[float, float] | None = None,
) -> None:
    """Create and save an overlaid histogram comparing two distributions.

    Args:
        values_cpp: Sequence of values from lovamap-cpp
        values_matlab: Sequence of values from MATLAB
        out_path: Path to save the plot (parent directories will be created)
        descriptor_name: Name of the descriptor (used in title)
        filename: Source filename (used in title)
        bins: Number of bins (defaults to 'auto' / sym choice)
        density: If True, plot probability density (normalized)
        figsize: Figure size in inches
        xlim: Optional x-axis limits (min, max)
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    a = np.asarray(values_cpp)
    b = np.asarray(values_matlab)

    # Filter out NaNs and infinite values
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]

    if xlim is not None:
        x_min, x_max = xlim
        a = a[(a >= x_min) & (a <= x_max)]
        b = b[(b >= x_min) & (b <= x_max)]

    # If either distribution is empty after filtering, skip plotting
    if a.size == 0 or b.size == 0:
        return

    # Choose bins: if not provided, compute joint bins
    if bins is None:
        combined = np.concatenate([a.ravel(), b.ravel()])
        # use Freedman–Diaconis rule as default heuristic
        q25, q75 = np.percentile(combined, [25, 75])
        iqr = max(q75 - q25, 1e-9)
        bin_width = 2 * iqr * (len(combined) ** (-1 / 3)) if len(combined) > 0 else 1.0
        if bin_width <= 0:
            bins = 40
        else:
            span = combined.max() - combined.min() if len(combined) > 0 else 1.0
            # handle zero-span (all values equal)
            if span == 0:
                center = float(combined.max())
                span = max(abs(center) * 1e-6, 1e-6)
                combined_min = center - span / 2
                combined_max = center + span / 2
            else:
                combined_min = combined.min()
                combined_max = combined.max()

            bins = max(10, int(np.ceil((combined_max - combined_min) / bin_width)))

    plt.figure(figsize=figsize)
    sns.set_style("whitegrid")

    # Plot KDE / histogram overlays
    # If combined_min/combined_max were set for zero-span correction, pass binrange
    hist_kwargs = dict(bins=bins, color="#1f77b4", stat=("density" if density else "count"), kde=False, alpha=0.45)
    sns.histplot(a, label="lovamap-cpp", **hist_kwargs)
    hist_kwargs.update(dict(color="#ff7f0e"))
    sns.histplot(b, label="matlab", **hist_kwargs)

    plt.title(f"{filename} — {descriptor_name}")
    plt.xlabel(descriptor_name)
    plt.ylabel("Density" if density else "Count")
    if xlim is not None:
        plt.xlim(xlim)
    plt.legend()

    plt.tight_layout()
    plt.savefig(out_path)
    # optional console feedback
    try:
        print(f"Saved plot: {out_path}")
    except Exception:
        pass
    plt.close()
