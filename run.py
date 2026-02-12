"""
Entry point for LOVAMAP workflows: comparison and data cleaning.

Available workflows:
  - comparison: Compare LOVAMAP C++ outputs against MATLAB gold-standard outputs
  - clean: Process and filter particle geometry data by bounding box constraints

Usage examples:

  # Run comparison workflow (default)
  python run.py comparison

  # Run comparison with custom paths
  python run.py comparison --cpp-dir /path/to/cpp --matlab-dir /path/to/matlab

  # Run data cleaning workflow with defaults
  python run.py clean

  # Run data cleaning with custom y-max bound
  python run.py clean --y-max 600.0
"""

import argparse
from pathlib import Path

from config.data_cleaning import load_cleaning_config
from config.comparison import load_comparison_config
from core.comparison import run_comparison
from core.data_cleaning import batch_clean_raw_data


def run_comparison_workflow(args) -> None:
    """Execute the comparison workflow."""
    plot_descriptors = None
    if args.plot_descriptors:
        plot_descriptors = [s.strip() for s in args.plot_descriptors.split(",") if s.strip()]
    cfg = load_comparison_config(
        cpp_dir=args.cpp_dir,
        matlab_dir=args.matlab_dir,
        pairs_file=args.pairs,
        out_file=args.out,
        make_plots=args.make_plots,
        plot_descriptors=plot_descriptors,
    )

    cfg.out_file.parent.mkdir(parents=True, exist_ok=True)

    print("=== LOVAMAP Comparison Workflow ===")
    print(f"  C++ dir     : {cfg.cpp_dir}")
    print(f"  MATLAB dir  : {cfg.matlab_dir}")
    print(f"  Pairs file  : {cfg.pairs_file}")
    print(f"  Output file : {cfg.out_file}")
    print(f"  Make plots  : {cfg.make_plots}")
    if cfg.make_plots:
        print(f"  Plot keys   : {cfg.plot_descriptors}")
    print(f"  Descriptors : {cfg.descriptors_to_compare}")
    print()

    run_comparison(cfg)


def run_cleaning_workflow(args) -> None:
    """Execute the data cleaning workflow."""
    cfg = load_cleaning_config(
        raw_dir=args.raw_dir,
        clean_dir=args.clean_dir,
        x_max=args.x_max,
        y_max=args.y_max,
        z_max=args.z_max,
        dx=args.dx
    )

    print("=== LOVAMAP Data Cleaning Workflow ===")
    print(f"  Raw data dir  : {cfg.raw_dir}")
    print(f"  Clean data dir: {cfg.clean_dir}")
    print(f"  X-max bound   : {cfg.x_max}")
    print(f"  Y-max bound   : {cfg.y_max}")
    print(f"  Z-max bound   : {cfg.z_max}")
    print(f"  Dx threshold  : {cfg.dx}")
    print()

    batch_clean_raw_data(
        cfg.raw_dir,
        cfg.clean_dir,
        x_max=cfg.x_max,
        y_max=cfg.y_max,
        z_max=cfg.z_max,
        dx=cfg.dx,
        verbose=cfg.verbose,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LOVAMAP workflow runner: comparison or data cleaning.",
    )

    subparsers = parser.add_subparsers(dest="workflow", help="Workflow to run")
    subparsers.required = True

    # --- Comparison subcommand ---
    comp_parser = subparsers.add_parser(
        "comparison",
        help="Compare LOVAMAP C++ outputs against MATLAB gold-standard outputs.",
    )
    comp_parser.add_argument(
        "--cpp-dir",
        type=str,
        help="Directory containing LOVAMAP C++ JSON outputs (overrides default).",
    )
    comp_parser.add_argument(
        "--matlab-dir",
        type=str,
        help="Directory containing MATLAB Excel outputs (overrides default).",
    )
    comp_parser.add_argument(
        "--pairs",
        type=str,
        help="CSV file mapping IDs to MATLAB/C++ outputs (overrides default).",
    )
    comp_parser.add_argument(
        "--out",
        type=str,
        help="Output summary Excel file path (overrides default).",
    )
    plot_group = comp_parser.add_mutually_exclusive_group()
    plot_group.add_argument(
        "--plots",
        dest="make_plots",
        action="store_true",
        help="Enable plotting.",
    )
    plot_group.add_argument(
        "--no-plots",
        dest="make_plots",
        action="store_false",
        help="Disable plotting.",
    )
    plot_group.set_defaults(make_plots=None)
    comp_parser.add_argument(
        "--plot-descriptors",
        type=str,
        help="Comma-separated descriptor keys to plot (defaults from config).",
    )
    comp_parser.set_defaults(func=run_comparison_workflow)

    # --- Cleaning subcommand ---
    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean particle geometry data by filtering based on bounding box constraints.",
    )
    clean_parser.add_argument(
        "--raw-dir",
        type=str,
        default=None,
        help="Directory containing raw .dat files (default: config default).",
    )
    clean_parser.add_argument(
        "--clean-dir",
        type=str,
        default=None,
        help="Directory to save cleaned .dat files (default: config default).",
    )
    clean_parser.add_argument(
        "--y-max",
        type=float,
        default=None,
        help="Maximum y-extent for particles (if omitted, no y filtering).",
    )
    clean_parser.add_argument(
        "--x-max",
        type=float,
        default=None,
        help="Maximum x-extent for particles (if omitted, no x filtering).",
    )
    clean_parser.add_argument(
        "--z-max",
        type=float,
        default=None,
        help="Maximum z-extent for particles (if omitted, no z filtering).",
    )
    clean_parser.add_argument(
        "--dx",
        type=float,
        default=None,
        help="Optional threshold added to (center+radius) when testing against bounds (default from config if omitted).",
    )
    clean_parser.set_defaults(func=run_cleaning_workflow)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
