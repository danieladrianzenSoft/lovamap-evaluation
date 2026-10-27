"""
Entry point for LOVAMAP workflows: comparison, data cleaning, and API submission.

Available workflows:
  - comparison: Compare LOVAMAP C++ outputs against MATLAB gold-standard outputs
  - clean: Process and filter particle geometry data by bounding box constraints
  - submit: Submit scaffolds to LOVAMAP Core API and download results
  - pipeline: Submit scaffolds to API, then automatically run comparison

Usage examples:

  # Run comparison workflow
  python run.py comparison

  # Run comparison with custom paths
  python run.py comparison --cpp-dir /path/to/cpp --matlab-dir /path/to/matlab

  # Run data cleaning workflow with defaults (filters z > 600)
  python run.py clean

  # Run data cleaning with custom z-max bound
  python run.py clean --z-max 600.0

  # Submit all scaffolds to API, download results
  python run.py submit

  # Submit specific files only
  python run.py submit --files "labeledDomain_ellipsoids_100_v1.json,beadInfo_square100.dat"

  # Full pipeline: submit + compare
  python run.py pipeline

  # Full pipeline with custom timeout and no plots
  python run.py pipeline --timeout 300 --no-plots

  # Compare with existing local results
  python run.py comparison --cpp-dir data/descriptors/cpp/batch_01072026
"""

import argparse
from pathlib import Path

from config.data_cleaning import load_cleaning_config
from config.comparison import load_comparison_config, DEFAULT_CPP_BASE, _find_latest_batch
from config.submission import load_submission_config
from core.comparison import run_comparison
from core.data_cleaning import batch_clean_raw_data
from core.submission import run_submission
from core.statistics import run_statistics, run_reduce


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
        cpp_interior_only=args.interior_only,
        rel_diff_threshold=args.rel_diff_threshold,
    )

    cfg.out_file.parent.mkdir(parents=True, exist_ok=True)

    print("=== LOVAMAP Comparison Workflow ===")
    print(f"  C++ dir     : {cfg.cpp_dir}")
    print(f"  MATLAB dir  : {cfg.matlab_dir}")
    print(f"  Pairs file  : {cfg.pairs_file}")
    print(f"  Output file : {cfg.out_file}")
    print(f"  Interior only: {cfg.cpp_interior_only}")
    print(f"  Make plots  : {cfg.make_plots}")
    if cfg.make_plots:
        print(f"  Plot keys   : {cfg.plot_descriptors}")
    print(f"  Descriptors : {cfg.descriptors_to_compare}")
    print(f"  Rel diff thr: {cfg.rel_diff_threshold}")
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
    )

    print("=== LOVAMAP Data Cleaning Workflow ===")
    print(f"  Raw data dir  : {cfg.raw_dir}")
    print(f"  Clean data dir: {cfg.clean_dir}")
    print(f"  X-max bound   : {cfg.x_max}")
    print(f"  Y-max bound   : {cfg.y_max}")
    print(f"  Z-max bound   : {cfg.z_max}")
    print()

    batch_clean_raw_data(
        cfg.raw_dir,
        cfg.clean_dir,
        x_max=cfg.x_max,
        y_max=cfg.y_max,
        z_max=cfg.z_max,
        verbose=cfg.verbose,
    )


def run_submit_workflow(args) -> None:
    """Execute the API submission workflow."""
    scaffold_files = None
    if args.files:
        scaffold_files = [s.strip() for s in args.files.split(",") if s.strip()]

    cfg = load_submission_config(
        api_base_url=args.api_url,
        scaffold_dirs=args.scaffold_dir,
        output_dir=args.output_dir,
        dx=args.dx,
        poll_interval=args.poll_interval,
        job_timeout=args.timeout,
        scaffold_files=scaffold_files,
    )

    run_submission(cfg)


def run_pipeline_workflow(args) -> None:
    """Execute the full pipeline: submit + compare."""
    scaffold_files = None
    if args.files:
        scaffold_files = [s.strip() for s in args.files.split(",") if s.strip()]

    sub_cfg = load_submission_config(
        api_base_url=args.api_url,
        scaffold_dirs=args.scaffold_dir,
        output_dir=args.output_dir,
        dx=args.dx,
        poll_interval=args.poll_interval,
        job_timeout=args.timeout,
        scaffold_files=scaffold_files,
    )

    summary = run_submission(sub_cfg)
    output_dir = summary["output_dir"]

    succeeded = sum(1 for r in summary["results"] if r["status"] == "success")
    if succeeded == 0:
        print("\n[WARN] No successful submissions — skipping comparison.")
        return

    print(f"\n--- Running comparison with C++ dir: {output_dir} ---\n")

    plot_descriptors = None
    if args.plot_descriptors:
        plot_descriptors = [s.strip() for s in args.plot_descriptors.split(",") if s.strip()]

    comp_cfg = load_comparison_config(
        cpp_dir=output_dir,
        matlab_dir=args.matlab_dir,
        pairs_file=args.pairs,
        out_file=args.out,
        make_plots=args.make_plots,
        plot_descriptors=plot_descriptors,
        cpp_interior_only=args.interior_only,
        rel_diff_threshold=args.rel_diff_threshold,
    )

    comp_cfg.out_file.parent.mkdir(parents=True, exist_ok=True)

    print("=== LOVAMAP Comparison Workflow ===")
    print(f"  C++ dir     : {comp_cfg.cpp_dir}")
    print(f"  MATLAB dir  : {comp_cfg.matlab_dir}")
    print(f"  Pairs file  : {comp_cfg.pairs_file}")
    print(f"  Output file : {comp_cfg.out_file}")
    print(f"  Interior only: {comp_cfg.cpp_interior_only}")
    print(f"  Make plots  : {comp_cfg.make_plots}")
    if comp_cfg.make_plots:
        print(f"  Plot keys   : {comp_cfg.plot_descriptors}")
    print(f"  Descriptors : {comp_cfg.descriptors_to_compare}")
    print(f"  Rel diff thr: {comp_cfg.rel_diff_threshold}")
    print()

    run_comparison(comp_cfg)


def run_stats_workflow(args) -> None:
    """Execute the descriptor statistics workflow."""
    source_format = args.format
    # Support both --input-dir and legacy --cpp-dir
    explicit_dir = args.input_dir or getattr(args, "cpp_dir_compat", None)
    input_dir = Path(explicit_dir) if explicit_dir else (
        _find_latest_batch(DEFAULT_CPP_BASE) if source_format == "cpp" else None
    )
    if input_dir is None:
        print("[ERROR] --input-dir is required for matlab format.")
        return

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = input_dir / "descriptor_statistics.csv"
    interior_only = True if args.interior_only is None else args.interior_only

    print("=== LOVAMAP Descriptor Statistics ===")
    print(f"  Input dir     : {input_dir}")
    print(f"  Format        : {source_format}")
    print(f"  Output CSV    : {out_path}")
    if source_format == "cpp":
        print(f"  Interior only : {interior_only}")
    print()

    run_statistics(input_dir, out_path, interior_only=interior_only, source_format=source_format)


def run_reduce_workflow(args) -> None:
    """Execute the feature reduction workflow."""
    if args.input:
        stats_csv = Path(args.input)
    else:
        cpp_dir = Path(args.cpp_dir) if args.cpp_dir else _find_latest_batch(DEFAULT_CPP_BASE)
        stats_csv = cpp_dir / "descriptor_statistics.csv"

    if not stats_csv.exists():
        print(f"[ERROR] Statistics CSV not found: {stats_csv}")
        print("        Run 'python run.py stats' first to generate it.")
        return

    out_dir = Path(args.out_dir) if args.out_dir else stats_csv.parent

    print("=== LOVAMAP Feature Reduction ===")
    print(f"  Input CSV     : {stats_csv}")
    print(f"  Output dir    : {out_dir}")
    print(f"  Threshold     : |r| >= {args.threshold}")
    print()

    run_reduce(stats_csv, out_dir, threshold=args.threshold)


def _add_submission_args(parser: argparse.ArgumentParser) -> None:
    """Add submission-related arguments to a parser."""
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="LOVAMAP Core API base URL (default: https://api.lovamap.com).",
    )
    parser.add_argument(
        "--scaffold-dir",
        type=str,
        nargs="+",
        default=None,
        help="One or more directories containing scaffold files (default: data/scaffolds/clean).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save downloaded results (default: data/descriptors/cpp/batch_MMDDYYYY).",
    )
    parser.add_argument(
        "--dx",
        type=float,
        default=None,
        help="Voxel size dx for LOVAMAP (default: 2.0).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Seconds between status polls (default: 3.0).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Max seconds to wait for a single job (default: 120.0).",
    )
    parser.add_argument(
        "--files",
        type=str,
        default=None,
        help='Comma-separated scaffold filenames to submit (default: all in scaffold-dir).',
    )


def _add_comparison_args(parser: argparse.ArgumentParser) -> None:
    """Add comparison-related arguments to a parser."""
    parser.add_argument(
        "--matlab-dir",
        type=str,
        default=None,
        help="Directory containing MATLAB Excel outputs (overrides default).",
    )
    parser.add_argument(
        "--pairs",
        type=str,
        default=None,
        help="CSV file mapping IDs to MATLAB/C++ outputs (overrides default).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output summary Excel file path (overrides default).",
    )

    pore_group = parser.add_mutually_exclusive_group()
    pore_group.add_argument(
        "--interior-only",
        dest="interior_only",
        action="store_true",
        help="Filter C++ pores to interior-only (default).",
    )
    pore_group.add_argument(
        "--all-pores",
        dest="interior_only",
        action="store_false",
        help="Use all C++ pores (interior + boundary).",
    )
    pore_group.set_defaults(interior_only=None)

    plot_group = parser.add_mutually_exclusive_group()
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

    parser.add_argument(
        "--plot-descriptors",
        type=str,
        default=None,
        help="Comma-separated descriptor keys to plot (defaults from config).",
    )
    parser.add_argument(
        "--rel-diff-threshold",
        type=float,
        default=None,
        help="Relative difference threshold for scalar similarity (default: 0.01 = 1%%).",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LOVAMAP workflow runner: comparison, data cleaning, or API submission.",
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
    _add_comparison_args(comp_parser)
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
    clean_parser.set_defaults(func=run_cleaning_workflow)

    # --- Submit subcommand ---
    submit_parser = subparsers.add_parser(
        "submit",
        help="Submit scaffolds to LOVAMAP Core API and download results.",
    )
    _add_submission_args(submit_parser)
    submit_parser.set_defaults(func=run_submit_workflow)

    # --- Pipeline subcommand ---
    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Submit scaffolds to API, then run comparison on results.",
    )
    _add_submission_args(pipeline_parser)
    _add_comparison_args(pipeline_parser)
    pipeline_parser.set_defaults(func=run_pipeline_workflow)

    # --- Stats subcommand ---
    stats_parser = subparsers.add_parser(
        "stats",
        help="Compute summary statistics on C++ descriptor outputs and export to CSV.",
    )
    stats_parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="Directory containing JSON outputs (default: latest batch_* for cpp format).",
    )
    # Keep --cpp-dir as alias for backward compatibility
    stats_parser.add_argument(
        "--cpp-dir",
        type=str,
        default=None,
        dest="cpp_dir_compat",
        help=argparse.SUPPRESS,
    )
    stats_parser.add_argument(
        "--format",
        type=str,
        choices=["cpp", "matlab"],
        default="cpp",
        help="Input JSON format: 'cpp' (LOVAMAP C++) or 'matlab' (LOVAMAP MATLAB) (default: cpp).",
    )
    stats_parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output CSV path (default: <input-dir>/descriptor_statistics.csv).",
    )
    stats_pore_group = stats_parser.add_mutually_exclusive_group()
    stats_pore_group.add_argument(
        "--interior-only",
        dest="interior_only",
        action="store_true",
        help="Filter pores to interior-only (default, cpp format only).",
    )
    stats_pore_group.add_argument(
        "--all-pores",
        dest="interior_only",
        action="store_false",
        help="Use all pores (interior + boundary, cpp format only).",
    )
    stats_pore_group.set_defaults(interior_only=None)
    stats_parser.set_defaults(func=run_stats_workflow)

    # --- Reduce subcommand ---
    reduce_parser = subparsers.add_parser(
        "reduce",
        help="Identify redundant features via correlation clustering and produce a reduced CSV.",
    )
    reduce_parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to descriptor_statistics.csv (default: auto-detect from --cpp-dir).",
    )
    reduce_parser.add_argument(
        "--cpp-dir",
        type=str,
        default=None,
        help="Directory containing C++ outputs (used to find descriptor_statistics.csv).",
    )
    reduce_parser.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help="Output directory for reduced CSV and mapping (default: same as input CSV).",
    )
    reduce_parser.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="Minimum |Spearman r| to consider features redundant (default: 0.95).",
    )
    reduce_parser.set_defaults(func=run_reduce_workflow)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
