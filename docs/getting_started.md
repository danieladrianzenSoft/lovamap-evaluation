# Getting Started

This guide explains what this project does, how it works, and how to use it. It's written for someone new to the codebase.

## What is LOVAMAP?

LOVAMAP is software that analyzes the internal structure of porous scaffolds (3D materials with holes/pores, used in biomedical engineering). You give it a scaffold file describing the shape and position of particles, and it computes **descriptors** — numerical measurements like pore volume, surface area, aspect ratio, number of connected pores, etc.

There are two versions of LOVAMAP:
- **MATLAB version** (original): runs locally, outputs Excel files
- **C++ version** (rewrite): runs as a cloud API at `core.lovamap.com`, outputs JSON files

## What Does This Repo Do?

This repo answers one question: **does the C++ version produce the same results as the MATLAB version?**

It does this by:
1. Submitting scaffold files to the C++ API and downloading the results
2. Loading the corresponding MATLAB results (pre-computed Excel files)
3. Comparing every descriptor between the two, using statistical tests
4. Producing a summary report showing which descriptors match and which differ

## Key Concepts

- **Scaffold**: a file (`.dat` or `.json`) describing the 3D arrangement of particles in a material
- **Descriptor**: a measurement computed by LOVAMAP (e.g., pore volume, surface area, aspect ratio)
  - **Global descriptors**: one value per scaffold (e.g., total number of pores)
  - **Pore descriptors**: one value per pore (e.g., volume of each individual pore)
  - **Other descriptors**: one value per particle, door, or path
- **Interior pores**: pores fully inside the scaffold (not touching the boundary). MATLAB files only contain interior pores. C++ files contain all pores but we filter to interior-only for comparison.

## Project Structure

```
LOVAMAP_Evaluation/
├── run.py                  # CLI entry point — run everything from here
├── config/                 # Default settings for each workflow
├── core/                   # The actual code that does the work
│   ├── mappings.py         # Maps MATLAB column names <-> C++ JSON keys
│   ├── submission.py       # Sends scaffolds to the C++ API
│   ├── comparison.py       # Compares MATLAB vs C++ results
│   ├── data_cleaning.py    # Filters raw scaffold files
│   └── statistics.py       # Summary stats and feature reduction
├── data/
│   ├── scaffolds/
│   │   ├── raw/            # Original scaffold files
│   │   └── clean/          # Filtered scaffold files (used for submission)
│   └── descriptors/
│       ├── matlab/         # MATLAB Excel outputs (pre-computed)
│       └── cpp/            # C++ JSON outputs (downloaded from API)
├── file_pairs.csv          # Maps scaffold IDs to their MATLAB and C++ filenames
├── file_pairs_test.csv     # Small subset (3 scaffolds) for quick test runs
└── docs/
    ├── getting_started.md          # This file
    ├── mapping_status.md           # Complete list of all descriptors and their mapping status
    └── descriptor_analysis_summary.md  # Results from a large-scale analysis
```

## Setup

```bash
# 1. Create and activate the conda environment
conda create -n lovamap-evaluation python=3.10
conda activate lovamap-evaluation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up API credentials (only needed for submitting to the C++ API)
cp .env.template .env
# Edit .env and fill in your LOVAMAP email and password
```

## Quick Start: Run a Test Comparison

The fastest way to see the system work is to compare pre-existing results using just 3 scaffolds:

```bash
python run.py comparison --pairs file_pairs_test.csv
```

This compares the MATLAB Excel files against C++ JSON files for 3 scaffolds (spheres, ellipsoids, rods) and produces a summary Excel file in `data/comparison_analysis/`.

To compare all 12 scaffolds:

```bash
python run.py comparison
```

## How the C++ Submission Works

When you run `python run.py submit`, here's what happens step by step:

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Computer                            │
│                                                             │
│  For each scaffold file (one at a time, sequentially):      │
│                                                             │
│  1. POST /jobs  ─────────────────────►  LOVAMAP Core API    │
│     (upload scaffold file)              (cloud server)      │
│                                              │              │
│  2. Poll GET /jobs/status ◄──────────────────┘              │
│     (every 3 seconds, "is it done yet?")                    │
│     ...wait...wait...wait...                                │
│                                              │              │
│  3. GET /jobs/results  ◄─────────────────────┘              │
│     (download the descriptor JSON)                          │
│                                                             │
│  4. Save JSON to data/descriptors/cpp/batch_MMDDYYYY/       │
│                                                             │
│  ──► Move to next scaffold file                             │
└─────────────────────────────────────────────────────────────┘
```

**Key details:**
- It processes scaffolds **one at a time** — submit, wait for completion, download, then move to the next
- Each scaffold typically takes 30-120 seconds to process on the server
- If the process is interrupted, you can rerun the same command — it **skips scaffolds whose output already exists**
- The API requires authentication (email/password in `.env`). Tokens refresh automatically if they expire.

For large batches (hundreds of scaffolds), run it in the background:
```bash
nohup python run.py submit --output-dir data/descriptors/cpp/batch_all > submit_all.log 2>&1 &
tail -f submit_all.log  # watch progress (Ctrl+C to stop watching, job keeps running)
```

## How the Comparison Works

When you run `python run.py comparison`, here's what happens:

1. **Load file pairs** from `file_pairs.csv` — this maps each test ID to its MATLAB Excel file and C++ JSON file
2. **For each pair:**
   - Read the MATLAB Excel file (globals from rows 1-2, per-pore data from row 3+)
   - Read the C++ JSON file (filter to interior pores only)
   - For each mapped descriptor (defined in `core/mappings.py`):
     - **Scalars**: compute absolute and relative difference
     - **Vectors**: run KS test, Wasserstein distance, RMSE on the two distributions
3. **Write results** to an Excel file with three sheets:
   - `scalar_descriptors`: per-file scalar comparison results
   - `vector_descriptors`: per-file vector comparison results with statistical tests
   - `descriptor_summary`: one row per descriptor showing what % of files were "similar"

## Descriptor Mappings

The MATLAB and C++ versions use different names for the same descriptors. For example:
- MATLAB: `Volume (pL)` → C++: `Volume` (also needs dividing by 1000 for unit conversion)
- MATLAB: `# Particle Edges` → C++: `NumEdges`

All mappings are defined in `core/mappings.py`. See `docs/mapping_status.md` for the complete list.

Currently mapped: **73 descriptors** total. Some may have empty values in C++ depending on the API version (e.g., path, bottleneck, ligand descriptors). The comparison handles this automatically — if either side has no data, it reports `n_cpp=0` or `n_matlab=0`.

## Available Workflows

| Command | What it does |
|---|---|
| `python run.py comparison` | Compare existing MATLAB and C++ results for the same scaffolds |
| `python run.py submit` | Send scaffold files to the C++ API and download results |
| `python run.py pipeline` | Submit + compare in one step |
| `python run.py clean` | Remove particles that cross the bounding box, so C++ gets the same geometry MATLAB used |
| `python run.py stats` | Summarize one source's descriptors into a flat CSV (not a MATLAB vs C++ comparison) |
| `python run.py reduce` | Remove redundant columns from the stats CSV via correlation clustering |

Every command supports `--help` for full option details (e.g. `python run.py comparison --help`).

### Core Workflows (MATLAB vs C++ validation)

These are the main workflows for validating the C++ rewrite against the MATLAB original.

#### `python run.py comparison`

**Compares pre-existing MATLAB and C++ results for the same scaffolds.** It does NOT submit anything to the API — it just reads files that are already on disk.

It loads pairs of files from `file_pairs.csv` (each row maps a scaffold ID to its MATLAB Excel file and C++ JSON file), then for each descriptor in `core/mappings.py`, compares the two. Scalars are compared by relative difference; vectors are compared using KS tests, Wasserstein distance, and RMSE.

Output: an Excel file with per-descriptor, per-scaffold comparison results and a summary sheet.

#### `python run.py submit`

**Sends scaffold files to the LOVAMAP C++ API and downloads the results.** This is how you get C++ outputs for scaffolds you haven't analyzed yet. See "How the C++ Submission Works" above for the full flow.

#### `python run.py pipeline`

**Runs `submit` then `comparison` back-to-back.** Convenience command for when you want to submit new scaffolds and immediately compare the results against MATLAB.

#### `python run.py clean`

**Preprocesses raw scaffold files before submission.** MATLAB removes particles whose edges cross the scaffold's bounding box before computing descriptors. If we want to compare C++ results against MATLAB fairly, we need to send C++ the same geometry — so this workflow removes those particles from the raw `.dat`/`.json` files, producing cleaned versions in `data/scaffolds/clean/`.

Without this step, C++ would be analyzing a slightly different geometry than MATLAB did, and the comparison would show differences that aren't about the algorithm but about the input.

### Analysis Workflows (not about MATLAB vs C++)

These workflows are separate from the MATLAB-vs-C++ validation. They're for analyzing descriptor outputs on their own — e.g., to study how scaffolds differ from each other.

#### `python run.py stats`

**Summarizes each scaffold's descriptors into a flat CSV.** For each scaffold JSON (C++ or MATLAB), it computes 9 summary statistics per vector descriptor (min, Q1, median, Q3, max, mean, mode, standard error, peak frequency) and includes globals as-is. The output is one row per scaffold, one column per statistic.

This is useful for downstream analysis like clustering scaffolds by their properties, or visualizing how descriptors vary across scaffold types. It does NOT compare MATLAB vs C++.

#### `python run.py reduce`

**Identifies redundant descriptor features and removes them.** Many descriptors are highly correlated with each other across scaffolds (e.g., Volume_mean and Volume_median move together). This workflow uses Spearman correlation and hierarchical clustering to group correlated features, then keeps one representative per group.

This is a dimensionality reduction step — useful if you want to cluster or classify scaffolds but don't want hundreds of correlated columns confusing the analysis. It requires running `stats` first to produce the input CSV.

## Common Tasks

### Run comparison on a subset of scaffolds
```bash
python run.py comparison --pairs file_pairs_test.csv
```

### Run comparison with histogram plots
```bash
python run.py comparison --plots --plot-descriptors PoreVolume,PoreSurfaceArea,PoreAspectRatio
```

### Submit specific scaffolds only
```bash
python run.py submit --files "beadInfo_square100.dat,labeledDomain_ellipsoids_100_v1.json"
```

### Submit and compare in one step
```bash
python run.py pipeline --pairs file_pairs_test.csv
```

## What Still Needs Work

### Dashboard / Summary Improvements
The comparison output is currently an Excel file. A nicer dashboard or visual summary would make it easier to quickly see which descriptors agree and which differ.

### Adding New Descriptor Mappings
If LOVAMAP adds new descriptors, they need to be added to `core/mappings.py`. See the existing entries as examples. Each mapping needs:
1. A unique key (e.g. `PoreNewDescriptor`)
2. The MATLAB Excel column header (e.g. `New Descriptor (um)`)
3. The C++ JSON key (e.g. `NewDescriptor`)
4. A `cpp_divisor` if the units differ (usually 1)

### Adding New Scaffold Pairs
To compare a new scaffold:
1. Put the MATLAB Excel file in `data/descriptors/matlab/`
2. Put the scaffold file in `data/scaffolds/clean/` (or submit it via `python run.py submit`)
3. Add a row to `file_pairs.csv` mapping the ID to both filenames

## Further Reading

- `docs/mapping_status.md` — complete list of all descriptors with MATLAB/C++ names
- `docs/descriptor_analysis_summary.md` — results from analyzing 400+ scaffolds
- `README.md` — full reference for all command-line options
