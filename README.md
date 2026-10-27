# LOVAMAP Evaluation

This repository compares outputs between two versions of the LOVAMAP software, provides a data-cleaning workflow for raw particle `.dat` files, automates job submission to the LOVAMAP Core API, and includes statistical analysis tools for descriptor outputs.

## Project Structure

- `run.py` — CLI entry point for all workflows
- `config/` — workflow configuration defaults
- `core/` — workflow implementations
- `data/` — input data and generated outputs
- `file_pairs.csv` — mapping of test IDs to MATLAB/C++ output filenames
- `requirements.txt` — Python dependencies
- `.env.template` — template for API credentials

## Setup

```bash
python -m pip install -r requirements.txt
```

For API submission workflows (`submit` and `pipeline`), create a `.env` file from the template:

```bash
cp .env.template .env
```

Then fill in your LOVAMAP Core API credentials:

```
LOVAMAP_EMAIL=your_email@example.com
LOVAMAP_PASSWORD=your_password
```

## Workflows

### 1) Comparison Workflow

Compares MATLAB Excel outputs against C++ JSON outputs using descriptor mappings in `core/mappings.py`.

Run:
```bash
python run.py comparison
```

Key options:
- `--cpp-dir PATH` — override C++ JSON directory (default: latest `batch_*` in `data/descriptors/cpp/`)
- `--matlab-dir PATH` — override MATLAB Excel directory
- `--pairs PATH` — override `file_pairs.csv`
- `--out PATH` — explicit output `.xlsx` path
- `--plots` / `--no-plots` — enable or disable plotting
- `--plot-descriptors KEY1,KEY2` — comma-separated descriptor keys to plot
- `--rel-diff-threshold FLOAT` — relative difference threshold for scalar similarity (default: 0.01 = 1%)

Defaults:
- If `--cpp-dir` is not provided, the most recently modified `batch_*` directory under `data/descriptors/cpp/` is used automatically. This means after running the `pipeline` or `submit` workflow, a subsequent `comparison` run will pick up the new results without needing to specify the path.
- If `--out` is not provided, outputs go to a timestamped folder under `data/comparison_analysis/`, e.g.
  `data/comparison_analysis/02122026_1610/comparison_summary.xlsx`
- Plotting defaults and selectable keys live in `config/comparison.py`.

Example:
```bash
# Run comparison with default settings and no plots
python run.py comparison

# Run comparison with plots for selected descriptors
python run.py comparison --plots --plot-descriptors PoreLongestLength,PoreAspectRatio,PoreLargestEnclosedSphere
```

### 2) Data Cleaning Workflow

Cleans raw scaffold data (`.dat` sphere particles and `.json` voxelized entities) by removing entities that exceed bounding box constraints.

Run:
```bash
python run.py clean
```

Key options:
- `--raw-dir PATH` — override raw data directory
- `--clean-dir PATH` — override output directory
- `--x-max FLOAT` — x bound (optional)
- `--y-max FLOAT` — y bound (optional)
- `--z-max FLOAT` — z bound (optional)
- `--dx FLOAT` — threshold added to `(center + radius)` when testing bounds

Defaults are defined in `config/data_cleaning.py`.

Example:
```bash
python run.py clean --z-max 600 --dx 2
```

### 3) API Submission Workflow

Submits scaffold files to the LOVAMAP Core API, polls for completion, and downloads the resulting descriptor JSON files.

**Resume support:** If a scaffold's output JSON already exists in the output directory, it is automatically skipped. This means you can safely restart the same command after a crash or interruption — it picks up where it left off.

Run:
```bash
python run.py submit
```

Key options:
- `--api-url URL` — API base URL (default: `https://core.lovamap.com`)
- `--scaffold-dir PATH [PATH ...]` — one or more directories containing scaffold files (default: `data/scaffolds/clean`)
- `--output-dir PATH` — directory to save results (default: `data/descriptors/cpp/batch_MMDDYYYY`)
- `--dx FLOAT` — voxel size (default: 2.0)
- `--poll-interval FLOAT` — seconds between status polls (default: 3.0)
- `--timeout FLOAT` — max seconds per job (default: 120.0)
- `--files LIST` — comma-separated filenames to submit (default: all files in scaffold dirs)

Example:
```bash
# Submit all scaffolds from default directory
python run.py submit

# Submit from multiple directories at once
python run.py submit --scaffold-dir /path/to/Jsons /path/to/Dats --output-dir data/descriptors/cpp/batch_all

# Submit specific files only
python run.py submit --files "beadInfo_square100.dat,labeledDomain_ellipsoids_100_v1.json"

# Submit with a longer timeout
python run.py submit --timeout 300
```

### 4) Pipeline Workflow

Combines submission and comparison into a single command: submits scaffolds to the API, downloads results, then runs the comparison workflow using the downloaded results as the C++ directory.

Run:
```bash
python run.py pipeline
```

Accepts all options from both `submit` and `comparison` workflows.

Example:
```bash
# Full pipeline with defaults
python run.py pipeline

# Pipeline with custom timeout and no plots
python run.py pipeline --timeout 300 --no-plots

# Pipeline for specific files with plotting
python run.py pipeline --files "beadInfo_square100.dat" --plots
```

### 5) Statistics Workflow

Computes summary statistics for each scaffold's C++ descriptor output and exports them to a single CSV. For each vector descriptor (pore + other), it computes: min, Q1, median, Q3, max, mean, mode (KDE-based), standard error, and peak frequency. Global descriptors are included as-is (excluding `Dx`, `DomainSize`, `AvgVoidAreaFraction`).

Pore descriptors are filtered to interior-only by default.

Run:
```bash
python run.py stats
```

Key options:
- `--cpp-dir PATH` — directory containing C++ JSON outputs (default: latest `batch_*`)
- `--out PATH` — output CSV path (default: `<cpp-dir>/descriptor_statistics.csv`)
- `--interior-only` / `--all-pores` — pore filtering (default: interior-only)

Example:
```bash
# Compute statistics for the latest batch
python run.py stats

# Compute for a specific batch
python run.py stats --cpp-dir data/descriptors/cpp/batch_all_scaffolds

# Include boundary pores
python run.py stats --all-pores
```

Output: A CSV with one row per scaffold and columns for each global descriptor and each vector descriptor's summary statistics (e.g. `Volume_min`, `Volume_q1`, ..., `Volume_peak_frequency`).

### 6) Feature Reduction Workflow

Identifies redundant features via Spearman correlation and hierarchical clustering, then produces a reduced feature set. Features with |Spearman r| above the threshold are grouped into clusters, and one representative is kept from each cluster (the most central member by mean intra-cluster correlation).

Run:
```bash
python run.py reduce
```

Key options:
- `--cpp-dir PATH` — directory containing C++ outputs; looks for `descriptor_statistics.csv` inside it (default: latest `batch_*`)
- `--input PATH` — path to a specific `descriptor_statistics.csv` (overrides `--cpp-dir`)
- `--out-dir PATH` — output directory for reduced CSV and mapping (default: same directory as input CSV)
- `--threshold FLOAT` — minimum |Spearman r| to consider features redundant (default: 0.95)

Example:
```bash
# Reduce features for the latest batch
python run.py reduce

# Use a more aggressive threshold
python run.py reduce --threshold 0.90

# Use a more conservative threshold
python run.py reduce --threshold 0.98

# Point to a specific statistics CSV
python run.py reduce --input data/descriptors/cpp/batch_all_scaffolds/descriptor_statistics.csv
```

Output:
- `descriptor_statistics_reduced.csv` — the reduced feature set (one row per scaffold, only representative features)
- `feature_cluster_mapping.csv` — lookup table showing which feature represents each cluster and which features were dropped

**Note:** The `stats` workflow must be run first to generate the input CSV.

## Running Long Jobs in the Background

For large submission batches (hundreds of scaffolds), run the process in the background so it survives terminal closure:

```bash
nohup python run.py submit \
  --scaffold-dir /path/to/Jsons /path/to/Dats \
  --output-dir data/descriptors/cpp/batch_all_scaffolds \
  --timeout 300 > submit_all.log 2>&1 &
```

Monitor progress:
```bash
tail -f submit_all.log
```

Press `Ctrl+C` to stop watching the log (the job keeps running).

Check how many scaffolds have completed:
```bash
ls data/descriptors/cpp/batch_all_scaffolds/*.json | wc -l
```

If the process crashes (network error, etc.), rerun the same command — the resume logic skips scaffolds whose output already exists.

Both stdout and stderr go to the log file, so any errors will appear there too.

## Descriptor Mappings

Descriptor names and their MATLAB/C++ mappings are defined in `core/mappings.py` under `DESCRIPTORS`.

If you add a new descriptor:
1. Add it to `DESCRIPTORS` in `core/mappings.py`.
2. Update any defaults in `config/comparison.py` as needed.

## Outputs

- **Comparison summary**: Excel file at the configured output path, containing three sheets:
  - `scalar_descriptors` — per-file scalar results (sorted by descriptor, then file ID), including a `similar` flag based on `rel_diff_threshold`
  - `vector_descriptors` — per-file vector results (sorted by descriptor, then file ID), with KS, Wasserstein, and RMSE statistics
  - `descriptor_summary` — cross-file aggregation with one row per descriptor, sorted by `pct_similar` ascending (most problematic descriptors first)
- Optional plots: `data/comparison_analysis/<timestamp>/plots/*.png`
- Cleaned `.dat` files: in the configured clean directory
- API submission results: `data/descriptors/cpp/batch_MMDDYYYY/*.json`
- **Statistics CSV**: `data/descriptors/cpp/<batch>/descriptor_statistics.csv` — one row per scaffold, all descriptor summary statistics
- **Reduced features CSV**: `data/descriptors/cpp/<batch>/descriptor_statistics_reduced.csv` — redundant features removed
- **Cluster mapping CSV**: `data/descriptors/cpp/<batch>/feature_cluster_mapping.csv` — shows which features were grouped and which representative was chosen
