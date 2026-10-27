"""
Data cleaning and preprocessing module for granular material scaffold data.

Handles reading .dat and .json scaffold files, filtering particles/entities
based on bounding box constraints, and writing cleaned data.

Supported formats:
  - .dat: Sphere particles with columns [x, y, z, radius].
    Removal criterion: (center + radius) > bound  (matches MATLAB).
  - .json: Voxelized entities (pores or beads) stored as 1D index ranges.
    Removal criterion: any voxel center > bound.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple, List
import numpy as np


def read_particle_data(file_path: Path) -> np.ndarray:
    """
    Read particle data from a .dat file, skipping any comment lines.
    
    Args:
        file_path: Path to the .dat file
        
    Returns:
        np.ndarray of shape (N, 4) with columns [x, y, z, radius]
        
    Raises:
        ValueError: If file cannot be parsed
    """
    particles = []
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comment lines
            if not line or line.startswith('#'):
                continue
            
            try:
                values = [float(val) for val in line.split()]
                if len(values) != 4:
                    raise ValueError(f"Expected 4 values (x, y, z, radius), got {len(values)}")
                particles.append(values)
            except ValueError as e:
                raise ValueError(f"Error parsing line: {line}\n{e}")
    
    if not particles:
        raise ValueError(f"No particle data found in {file_path}")
    
    return np.array(particles, dtype=np.float64)

def filter_particles_by_bounds(
    particles: np.ndarray,
    x_max: float | None = None,
    y_max: float | None = None,
    z_max: float | None = None,
) -> Tuple[np.ndarray, dict]:
    """
    Apply x/y/z center-based bounds to `particles` and return the filtered
    array along with a dict of boolean masks for each axis and the combined mask.

    The returned dict contains keys: 'mask_x', 'mask_y', 'mask_z', 'mask_any'.
    - mask_* are booleans where True indicates the particle is REMOVED by that axis.
    - mask_any is True where the particle is removed by any axis.
    """
    n = len(particles)
    mask_x = np.zeros(n, dtype=bool)
    mask_y = np.zeros(n, dtype=bool)
    mask_z = np.zeros(n, dtype=bool)
    # Remove particle if (center + radius) > bound.
    # Matches MATLAB: rmv_beads = (bead_data(:,3) + bead_data(:,4)) > 600;
    if x_max is not None:
        mask_x = (particles[:, 0] + particles[:, 3]) > x_max
    if y_max is not None:
        mask_y = (particles[:, 1] + particles[:, 3]) > y_max
    if z_max is not None:
        mask_z = (particles[:, 2] + particles[:, 3]) > z_max

    mask_any = mask_x | mask_y | mask_z
    filtered = particles[~mask_any]

    masks = {
        'mask_x': mask_x,
        'mask_y': mask_y,
        'mask_z': mask_z,
        'mask_any': mask_any,
    }

    return filtered, masks

## ── JSON scaffold helpers ──────────────────────────────────────────────


def read_json_scaffold(file_path: Path) -> dict:
    """Read a JSON scaffold file, handling the optional list wrapper."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    if isinstance(data, list):
        data = data[0]
    return data


def _detect_entity_key(data: dict) -> str:
    """Return the key that holds entity voxel data ('pores', 'bead_data', or 'beads')."""
    for key in ("pores", "bead_data", "beads"):
        if key in data:
            return key
    raise ValueError("JSON contains no recognized entity key (pores, bead_data, beads)")


def _expand_ranges(ranges: list[list[int]]) -> np.ndarray:
    """Expand 1-based inclusive ranges to a 0-based index array."""
    indices: list[int] = []
    for start, end in ranges:
        indices.extend(range(start - 1, end))  # 1-based inclusive → 0-based
    return np.array(indices, dtype=np.int64)


def _compute_grid_dims(data: dict) -> Tuple[int, int, int, list[float]]:
    """Return (nx, ny, nz, domain_bounds) from a parsed JSON scaffold.

    domain_bounds is always normalised to [x_min, x_max, y_min, y_max, z_min, z_max].
    Accepts both 3-value ([sx, sy, sz], origin at 0) and 6-value formats.
    """
    raw = data["domain_size"]
    voxel_size = data["voxel_size"]
    if len(raw) == 6:
        x_min, x_max_d, y_min, y_max_d, z_min, z_max_d = raw
    elif len(raw) == 3:
        x_min, y_min, z_min = 0.0, 0.0, 0.0
        x_max_d, y_max_d, z_max_d = raw
    else:
        raise ValueError(f"domain_size has {len(raw)} elements; expected 3 or 6")
    domain_bounds = [x_min, x_max_d, y_min, y_max_d, z_min, z_max_d]
    nx = int(round((x_max_d - x_min) / voxel_size))
    ny = int(round((y_max_d - y_min) / voxel_size))
    nz = int(round((z_max_d - z_min) / voxel_size))
    return nx, ny, nz, domain_bounds


def filter_json_entities_by_bounds(
    data: dict,
    x_max: float | None = None,
    y_max: float | None = None,
    z_max: float | None = None,
) -> Tuple[dict, dict]:
    """
    Filter entities from a JSON scaffold, removing any entity that has
    at least one voxel whose real-world center coordinate exceeds a bound.

    Returns (filtered_data, stats).
    """
    entity_key = _detect_entity_key(data)
    entities = data[entity_key]
    voxel_size = data["voxel_size"]
    nx, ny, nz, domain_size = _compute_grid_dims(data)
    x_min_d, _, y_min_d, _, z_min_d, _ = domain_size

    filtered_entities = {}
    removed_x = 0
    removed_y = 0
    removed_z = 0
    removed_ids: set[str] = set()

    for entity_id, ranges in entities.items():
        indices = _expand_ranges(ranges)
        remove = False

        if x_max is not None:
            x_real = x_min_d + (indices % nx + 0.5) * voxel_size
            if np.any(x_real > x_max):
                removed_x += 1
                remove = True

        if y_max is not None:
            y_real = y_min_d + ((indices // nx) % ny + 0.5) * voxel_size
            if np.any(y_real > y_max):
                removed_y += 1
                remove = True

        if z_max is not None:
            z_real = z_min_d + (indices // (nx * ny) + 0.5) * voxel_size
            if np.any(z_real > z_max):
                removed_z += 1
                remove = True

        if remove:
            removed_ids.add(entity_id)
        else:
            filtered_entities[entity_id] = ranges

    # Build output data, pruning metadata for removed entities
    filtered_data: dict = {}
    for key, value in data.items():
        if key == entity_key:
            filtered_data[key] = filtered_entities
        elif key == "pores_metadata" and isinstance(value, dict):
            filtered_data[key] = {k: v for k, v in value.items() if k not in removed_ids}
        elif key == "bead_count":
            filtered_data[key] = len(filtered_entities)
        elif key == "bead_voxel_count" and isinstance(value, dict):
            filtered_data[key] = {k: v for k, v in value.items() if k not in removed_ids}
        else:
            filtered_data[key] = value

    total = len(entities)
    kept = len(filtered_entities)
    removed_total = total - kept

    stats = {
        'total_entities': total,
        'filtered_entities': kept,
        'removed_entities': removed_total,
        'removed_by_x': removed_x,
        'removed_by_y': removed_y,
        'removed_by_z': removed_z,
        'removal_percentage': (removed_total / total * 100) if total > 0 else 0.0,
    }
    return filtered_data, stats


def clean_and_save_json(
    input_path: Path,
    output_path: Path,
    x_max: float | None = None,
    y_max: float | None = None,
    z_max: float | None = None,
    verbose: bool = True,
) -> dict:
    """Read a JSON scaffold, filter entities by bounds, and save the cleaned file."""
    data = read_json_scaffold(input_path)
    filtered_data, stats = filter_json_entities_by_bounds(
        data, x_max=x_max, y_max=y_max, z_max=z_max,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump([filtered_data], f, separators=(",", ":"))

    if verbose:
        print(f"Processed {input_path.name}")
        print(f"  Total entities: {stats['total_entities']}")
        print(f"  Kept: {stats['filtered_entities']}")
        print(f"  Removed (total): {stats['removed_entities']} ({stats['removal_percentage']:.2f}%)")
        print(f"    Removed by X: {stats['removed_by_x']}")
        print(f"    Removed by Y: {stats['removed_by_y']}")
        print(f"    Removed by Z: {stats['removed_by_z']}")
        print(f"  Saved to: {output_path}")

    stats['output_path'] = output_path
    return stats


## ── .dat sphere helpers ────────────────────────────────────────────────


def clean_and_save(
    input_path: Path,
    output_path: Path,
    x_max: float | None = None,
    y_max: float | None = None,
    z_max: float | None = None,
    verbose: bool = True,
) -> dict:
    """
    Read particle data, apply filtering, and save cleaned data.

    Args:
        input_path: Path to input .dat file
        output_path: Path to save cleaned .dat file
        x_max: If set, remove particles whose sphere extends beyond this x bound
        y_max: If set, remove particles whose sphere extends beyond this y bound
        z_max: If set, remove particles whose sphere extends beyond this z bound
        verbose: Print summary statistics (default: True)

    Returns:
        dict with keys:
            - 'total_particles': Number of particles read
            - 'filtered_particles': Number of particles kept
            - 'removed_particles': Number of particles removed
            - 'removal_percentage': Percentage of particles removed
            - 'output_path': Path where cleaned data was saved
    """
    # Read particles
    particles = read_particle_data(input_path)
    initial_count = len(particles)

    # Apply MATLAB-matching logic: remove if (center + radius) > bound
    filtered, masks = filter_particles_by_bounds(particles, x_max=x_max, y_max=y_max, z_max=z_max)

    removed_x = int(np.sum(masks['mask_x']))
    removed_y = int(np.sum(masks['mask_y']))
    removed_z = int(np.sum(masks['mask_z']))
    removed_total = int(np.sum(masks['mask_any']))
    final_count = len(filtered)
    removal_percentage = (removed_total / initial_count) * 100 if initial_count > 0 else 0.0

    # Save cleaned data
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(
        output_path,
        filtered,
        fmt='%.6f',
        delimiter=' ',
        comments='',  # Don't add any comment prefix
    )

    if verbose:
        print(f"Processed {input_path.name}")
        print(f"  Total particles: {initial_count}")
        print(f"  Kept: {final_count}")
        print(f"  Removed (total): {removed_total} ({removal_percentage:.2f}%)")
        print(f"    Removed by X: {removed_x}")
        print(f"    Removed by Y: {removed_y}")
        print(f"    Removed by Z: {removed_z}")
        print(f"  Saved to: {output_path}")

    return {
        'total_particles': initial_count,
        'filtered_particles': final_count,
        'removed_particles': removed_total,
        'removed_by_x': removed_x,
        'removed_by_y': removed_y,
        'removed_by_z': removed_z,
        'removal_percentage': removal_percentage,
        'output_path': output_path,
    }

def batch_clean_raw_data(
    raw_dir: Path,
    clean_dir: Path,
    x_max: float | None = None,
    y_max: float | None = None,
    z_max: float | None = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Process all .dat and .json files in raw_dir and save cleaned versions to clean_dir.

    Args:
        raw_dir: Directory containing raw .dat / .json scaffold files
        clean_dir: Directory to save cleaned files
        x_max: If set, remove entities exceeding this x bound
        y_max: If set, remove entities exceeding this y bound
        z_max: If set, remove entities exceeding this z bound
        verbose: Print summary for each file (default: True)

    Returns:
        List of result dicts for each processed file
    """
    raw_dir = Path(raw_dir)
    clean_dir = Path(clean_dir)

    dat_files = sorted(raw_dir.glob('*.dat'))
    json_files = sorted(raw_dir.glob('*.json'))

    if not dat_files and not json_files:
        raise ValueError(f"No .dat or .json files found in {raw_dir}")

    dat_results: list[dict] = []
    json_results: list[dict] = []

    # ── .dat files (sphere particles) ──
    for dat_file in dat_files:
        output_file = clean_dir / dat_file.name
        result = clean_and_save(
            dat_file, output_file,
            x_max=x_max, y_max=y_max, z_max=z_max,
            verbose=verbose,
        )
        dat_results.append(result)

    # ── .json files (voxelized entities) ──
    # Currently copied without filtering; JSON bound removal is not used
    # by the MATLAB workflow.  The clean_and_save_json() helper is kept
    # in case it is needed in the future.
    import shutil
    for json_file in json_files:
        output_file = clean_dir / json_file.name
        clean_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(json_file, output_file)
        if verbose:
            print(f"Copied {json_file.name} (no filtering applied)")

    if verbose:
        print(f"\n{'='*60}")
        print(f"Batch processing complete!")
        print(f"  .dat files : {len(dat_results)}")
        print(f"  .json files: {len(json_files)} (copied without filtering)")

        if dat_results:
            dat_removed = sum(r['removed_particles'] for r in dat_results)
            dat_kept = sum(r['filtered_particles'] for r in dat_results)
            print(f"  [.dat] Particles removed: {dat_removed}, kept: {dat_kept}")
            print(f"    Removed by X: {sum(r.get('removed_by_x', 0) for r in dat_results)}")
            print(f"    Removed by Y: {sum(r.get('removed_by_y', 0) for r in dat_results)}")
            print(f"    Removed by Z: {sum(r.get('removed_by_z', 0) for r in dat_results)}")

        print(f"{'='*60}")

    return dat_results
