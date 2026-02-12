"""
Data cleaning and preprocessing module for granular material scaffold data.

Handles reading .dat files containing particle geometry (x, y, z coordinates and radius),
filtering particles based on bounding box constraints, and writing cleaned data.
"""

from __future__ import annotations

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
    dx: float | None = None,
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
    # Remove particle if its sphere intersects the positive bound on any axis.
    # That is, if center + radius > max.
    # ensure dx numeric (0 when not provided)
    dx_val = 0.0 if dx is None else float(dx)
    if x_max is not None:
        mask_x = (particles[:, 0] + particles[:, 3] + dx_val) > x_max
    if y_max is not None:
        mask_y = (particles[:, 1] + particles[:, 3] + dx_val) > y_max
    if z_max is not None:
        mask_z = (particles[:, 2] + particles[:, 3] + dx_val) > z_max

    mask_any = mask_x | mask_y | mask_z
    filtered = particles[~mask_any]

    masks = {
        'mask_x': mask_x,
        'mask_y': mask_y,
        'mask_z': mask_z,
        'mask_any': mask_any,
    }

    return filtered, masks

def clean_and_save(
    input_path: Path,
    output_path: Path,
    x_max: float | None = None,
    y_max: float | None = None,
    z_max: float | None = None,
    dx: float | None = None,
    verbose: bool = True,
) -> dict:
    """
    Read particle data, apply filtering, and save cleaned data.
    
    Args:
        input_path: Path to input .dat file
        output_path: Path to save cleaned .dat file
        y_max: Maximum allowed y coordinate for particle voxel extent (default: 600.0)
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

    # Apply axis bounds using MATLAB logic (sphere intersects positive bounds)
    filtered, masks = filter_particles_by_bounds(particles, x_max=x_max, y_max=y_max, z_max=z_max, dx=dx)

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
    dx: float | None = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Process all .dat files in raw_dir and save cleaned versions to clean_dir.
    
    Args:
        raw_dir: Directory containing raw .dat files
        clean_dir: Directory to save cleaned .dat files
        y_max: Maximum allowed y coordinate for particle voxel extent (default: 600.0)
        verbose: Print summary for each file (default: True)
        
    Returns:
        List of result dicts from clean_and_save for each file
    """
    raw_dir = Path(raw_dir)
    clean_dir = Path(clean_dir)
    
    dat_files = sorted(raw_dir.glob('*.dat'))
    
    if not dat_files:
        raise ValueError(f"No .dat files found in {raw_dir}")
    
    results = []
    for dat_file in dat_files:
        output_file = clean_dir / dat_file.name
        result = clean_and_save(
            dat_file,
            output_file,
            x_max=x_max,
            y_max=y_max,
            z_max=z_max,
            dx = dx,
            verbose=verbose,
        )
        results.append(result)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Batch processing complete!")
        print(f"  Total files: {len(results)}")
        total_removed = sum(r['removed_particles'] for r in results)
        total_kept = sum(r['filtered_particles'] for r in results)
        total_removed_x = sum(r.get('removed_by_x', 0) for r in results)
        total_removed_y = sum(r.get('removed_by_y', 0) for r in results)
        total_removed_z = sum(r.get('removed_by_z', 0) for r in results)
        print(f"  Total particles removed: {total_removed}")
        print(f"  Total particles kept: {total_kept}")
        print(f"    Removed by X total: {total_removed_x}")
        print(f"    Removed by Y total: {total_removed_y}")
        print(f"    Removed by Z total: {total_removed_z}")
        print(f"{'='*60}")
    
    return results
