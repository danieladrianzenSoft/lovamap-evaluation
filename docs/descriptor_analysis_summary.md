# Descriptor Statistics & Feature Reduction Analysis

## Overview

This document summarizes the statistical analysis performed on LOVAMAP descriptor outputs from both the C++ (API) and MATLAB implementations. The goal was to compute summary statistics per scaffold, identify redundant features via correlation clustering, and produce reduced feature sets suitable for downstream analyses (e.g., scaffold clustering).

## Data Sources

### C++ (LOVAMAP API)

- **Scaffold inputs:** 456 scaffolds from two directories:
  - `/Users/dzen/Library/CloudStorage/Box-Box/Lindsay Riley/Electronic Notebook/Void Space Project/MIMC/Data/Domains/Particles/Simulated/Jsons/` (149 JSON files)
  - `/Users/dzen/Library/CloudStorage/Box-Box/Lindsay Riley/Electronic Notebook/Void Space Project/MIMC/Data/Domains/Particles/Simulated/Dats/` (307 DAT files)
- **Descriptor outputs:** `data/descriptors/cpp/batch_all_scaffolds/` (419 succeeded, 37 failed on API)
- **Format:** One JSON per scaffold, descriptors stored as `{name: {values: [...]}}` dicts

### MATLAB

- **Descriptor outputs:** `/Users/dzen/Library/CloudStorage/Box-Box/Lindsay Riley/Electronic Notebook/Void Space Project/MIMC/Data/Descriptors/json/Simulated/v2_compressed/` (64 JSON files containing 486 scaffolds total)
- **Format:** Each JSON may contain multiple scaffolds under `scaffolds[]`. Pore descriptor values are `{id, value}` dicts; other descriptor values are plain numbers.
- **Note:** These are already filtered to interior pores only (no `IsInterior` field).

## Analysis Pipeline

### Step 1: Summary Statistics (`python run.py stats`)

For each scaffold, we compute 9 summary statistics per vector descriptor (pore + other):
- min, Q1, median, Q3, max, mean, mode (KDE-based), standard error (SEM), peak frequency (KDE density at mode)

Global descriptors are included as single scalar values.

**Excluded globals:** `Dx`, `NumVoxels`, `DomainSize`, `AvgVoidAreaFraction` (resolution/domain metadata, not scaffold characteristics).

**Pore filtering (C++ only):** Interior-only by default (uses `IsInterior` mask). MATLAB data is already interior-only.

### Step 2: Feature Reduction (`python run.py reduce`)

Identifies redundant features using:
1. **Spearman rank correlation** across all scaffolds (robust to outliers and scale differences)
2. **Hierarchical clustering** (average linkage) on the distance matrix `1 - |r|`
3. **Threshold cut:** Features with |Spearman r| above the threshold are grouped into clusters
4. **Representative selection:** The most central member of each cluster (highest mean intra-cluster |r|) is kept

Two thresholds were evaluated: |r| >= 0.95 (conservative) and |r| >= 0.90 (aggressive).

## Results

### Descriptor Counts

|  | C++ | MATLAB |
|---|---|---|
| Scaffolds analyzed | 419 | 486 |
| Unique descriptors (raw LOVAMAP output) | 51 | 70 |
| Stat columns (after expanding to 9 stats each) | 323 | 494 |
| Reduced features (\|r\| >= 0.95) | 178 | 285 |
| Reduced features (\|r\| >= 0.90) | 132 | 212 |

### Why MATLAB has more descriptors

MATLAB produces 70 unique descriptors vs C++ 51. The C++ API does not populate 25 descriptors that MATLAB does (their value arrays are empty across all 419 scaffolds). These include:

- **Path descriptors:** PathLength, TortuositybyLength, TortuositybyVol, NumIntPoresPath, NumExtPoresPath, NumParticlesEnclosingIntPath, NumParticlesEnclosingExitPath
- **Bottleneck descriptors:** NumBottlenecksTotal, AvgBottleneckDiamTotal, NumBottlenecksDoors, AvgBottleneckDiamDoors
- **Region volumes:** RegionsVol0, RegionsVol10, RegionsVol30, RegionsVol60
- **Ligand/surface:** LigandConcentration, AccessibleLigand, SurfaceLigandConc, SurfaceAccessibleLigand, MeanLocalThickness, ParticleSA, OpenSA

C++ has 6 descriptors not in MATLAB:
- `xParticleCOM`, `yParticleCOM`, `zParticleCOM` (particle center of mass)
- `MaxNumEquidistantParticles` (named `MaxNumEquidistParticles` in MATLAB — spelling difference)
- `NumEdges` (named `NumParticleEdges` in MATLAB — naming difference)
- `TouchingParticle` (named `TouchingParticleCoord` in MATLAB — naming difference)

So the truly unique C++ descriptors are only the 3 COM fields.

### Naming Differences Between C++ and MATLAB

| C++ | MATLAB |
|---|---|
| `MaxNumEquidistantParticles` | `MaxNumEquidistParticles` |
| `NumEdges` | `NumParticleEdges` |
| `TouchingParticle` | `TouchingParticleCoord` |

## Output Files

### C++ Results

| File | Description |
|---|---|
| `data/descriptors/cpp/batch_all_scaffolds/descriptor_statistics.csv` | Full statistics: 419 scaffolds x 323 columns |
| `data/descriptors/cpp/batch_all_scaffolds/descriptor_statistics_reduced_095.csv` | Reduced at \|r\| >= 0.95: 419 x 178 |
| `data/descriptors/cpp/batch_all_scaffolds/descriptor_statistics_reduced_09.csv` | Reduced at \|r\| >= 0.90: 419 x 132 |
| `data/descriptors/cpp/batch_all_scaffolds/feature_cluster_mapping_095.csv` | Cluster mapping for 0.95 threshold |
| `data/descriptors/cpp/batch_all_scaffolds/feature_cluster_mapping_09.csv` | Cluster mapping for 0.90 threshold |

### MATLAB Results

| File | Description |
|---|---|
| `data/descriptors/matlab/batch_all_scaffolds/descriptor_statistics.csv` | Full statistics: 486 scaffolds x 494 columns |
| `data/descriptors/matlab/batch_all_scaffolds/descriptor_statistics_reduced_095.csv` | Reduced at \|r\| >= 0.95: 486 x 285 |
| `data/descriptors/matlab/batch_all_scaffolds/descriptor_statistics_reduced_09.csv` | Reduced at \|r\| >= 0.90: 486 x 212 |
| `data/descriptors/matlab/batch_all_scaffolds/feature_cluster_mapping_095.csv` | Cluster mapping for 0.95 threshold |
| `data/descriptors/matlab/batch_all_scaffolds/feature_cluster_mapping_09.csv` | Cluster mapping for 0.90 threshold |

## Commands to Reproduce

```bash
# C++ statistics
python run.py stats --input-dir data/descriptors/cpp/batch_all_scaffolds

# MATLAB statistics
python run.py stats --format matlab \
  --input-dir "/Users/dzen/Library/CloudStorage/Box-Box/Lindsay Riley/Electronic Notebook/Void Space Project/MIMC/Data/Descriptors/json/Simulated/v2_compressed" \
  --out data/descriptors/matlab/batch_all_scaffolds/descriptor_statistics.csv

# Feature reduction (run for each source and threshold)
python run.py reduce --input <path_to_descriptor_statistics.csv> --threshold 0.95
python run.py reduce --input <path_to_descriptor_statistics.csv> --threshold 0.90
```

## Notes

- The correlation analysis uses **Spearman** (rank-based), so it is not affected by outliers, skew, or different value scales. No normalization is needed for this step.
- For downstream clustering of scaffolds, a **log-transform + standardization** step should be applied to the reduced features before running distance-based algorithms (K-means, DBSCAN, etc.), since features have very different scales.
- The 0.95 threshold is recommended as the default — it is conservative enough to avoid merging features that might be independently informative, while still providing meaningful dimensionality reduction.
- With 419-486 scaffolds, the correlation estimates are statistically reliable.
