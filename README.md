# LOVAMAP Evaluation

This repository compares outputs between two versions of the LOVAMAP software and provides a data-cleaning workflow for raw particle `.dat` files.

## Project Structure

- `run.py` — CLI entry point for all workflows
- `config/` — workflow configuration defaults
- `core/` — workflow implementations
- `data/` — input data and generated outputs
- `file_pairs.csv` — mapping of test IDs to MATLAB/C++ output filenames
- `requirements.txt` — Python dependencies

## Setup

```bash
python -m pip install -r requirements.txt
```

## Workflows

### 1) Comparison Workflow

Compares MATLAB Excel outputs against C++ JSON outputs using descriptor mappings in `core/mappings.py`.

Run:
```bash
python run.py comparison
```

Key options:
- `--cpp-dir PATH` — override C++ JSON directory
- `--matlab-dir PATH` — override MATLAB Excel directory
- `--pairs PATH` — override `file_pairs.csv`
- `--out PATH` — explicit output `.xlsx` path
- `--plots` / `--no-plots` — enable or disable plotting
- `--plot-descriptors KEY1,KEY2` — comma-separated descriptor keys to plot

Defaults:
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

Cleans raw particle data by filtering particles based on bounding box constraints.

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

## Descriptor Mappings

Descriptor names and their MATLAB/C++ mappings are defined in `core/mappings.py` under `DESCRIPTORS`.

If you add a new descriptor:
1. Add it to `DESCRIPTORS` in `core/mappings.py`.
2. Update any defaults in `config/comparison.py` as needed.

## Outputs

- Comparison summary: Excel file at the configured output path
- Optional plots: `data/comparison_analysis/<timestamp>/plots/*.png`
- Cleaned `.dat` files: in the configured clean directory
