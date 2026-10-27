# Descriptor Mapping Status

This document lists every descriptor available in the MATLAB and C++ versions of LOVAMAP, along with the mapping status used by the comparison workflow.

Mappings are defined in `core/mappings.py`. The comparison workflow uses these mappings to align MATLAB Excel column headers with C++ JSON keys.

## How Mappings Work

Each descriptor has:
- **Key**: the internal name used in this repo (e.g. `PoreVolume`)
- **MATLAB name**: the Excel column header (e.g. `Volume (pL)`)
- **C++ name**: the JSON key (e.g. `Volume`)
- **cpp_divisor**: a number to divide the C++ value by, so it matches MATLAB units (default: 1 = no conversion)
- **Group**: `global` (one value per scaffold), `pore` (one value per pore), or `other` (one value per particle/door/path)

## Unit Conversions

| Descriptor | C++ unit | MATLAB unit | Divisor |
|---|---|---|---|
| PoreVolume | um^3 | pL (1 pL = 1000 um^3) | 1000 |
| PoreSurfaceArea | um^2 | um^2 / 1000 | 1000 |
| All others | same | same | 1 |

## Naming Differences

These descriptors exist in both versions but have different names:

| Key | MATLAB Name | C++ Name |
|---|---|---|
| PoreNumEdges | `# Particle Edges` | `NumEdges` |
| PoreIsotropy | `Isotropy` | `IsotropyAnisotropy` |
| TouchingParticleCoord | `Touching Particle Coord #` | `TouchingParticle` |
| MaxNumEquidistantParticles | `Max # Equidistant Particles` | `MaxNumEquidistantParticles` |

## Global Descriptors (20 total)

All are scalar (one value per scaffold).

| Key | MATLAB Name | C++ Name | Mapped | Notes |
|---|---|---|---|---|
| dx | dx | Dx | Yes | |
| NumVoxels | voxels | NumVoxels | Yes | |
| NumParticles | # Particles | NumParticles | Yes | |
| NumParticleContacts | # Particle Contacts | NumParticleContacts | Yes | |
| VFF | Void Vol Fraction | VFF | Yes | |
| ParticlePackingFraction | Particle Fraction | ParticlePackingFraction | Yes | |
| AvgVoidAreaFraction | Void Area Fraction | AvgVoidAreaFraction | Yes | |
| VFFIntPores | Void Vol Fraction of Interior Pores | VFFIntPores | Yes | |
| NumPoresTotal | # 3D Pores | NumTotalPores | Yes | |
| NumPoresInterior | # Interior 3D Pores | NumIntPores | Yes | |
| NumIntPoresDivParticles | # Int 3D-Pores / # Particles Surr Int Pores | NumIntPoresdivParticlesSurrIntPores | Yes | |
| NumExitDoors | # Exterior Doors | NumExitDoors | Yes | |
| NumIntDoors | # Interior Doors | NumIntDoors | Yes | |
| NumPaths | # Paths | NumPaths | Yes | |
| ParticleAdjMaxEig | Particle Adj Max Eig | ParticleAdjacencyMatrixEigenvalue | Yes | |
| PeakAdjMaxEig | Peak Adj Max Eig | PeakAdjacencyMatrixEigenvalue | Yes | |
| PoreAdjMaxEig | Pore Adj Max Eig | PoreAdjacencyMatrixEigenvalue | Yes | |
| MaxNumPeaksEdgePore | Max # Pks of Edge Pore | MaxNumPeaksAmongSurfacePores | Yes | |
| LigandHotspotsVolFrac | Ligand Hotspots Volume Fraction | LigandHotspotsVolFrac | Yes | |
| MaxNumEquidistantParticles | Max # Equidistant Particles | MaxNumEquidistantParticles | Yes | |

C++ also outputs `DomainSize` (e.g. "602 x 602 x 600"), which is a string and has no MATLAB equivalent. It is not mapped.

## Pore Descriptors (30 total)

All are vector (one value per pore). In the MATLAB Excel, these are columns 23+ (starting at "Volume (pL)"). In C++ JSON, these are under `poreDescriptors`.

### Populated in Both Versions (25)

| Key | MATLAB Name | C++ Name | Divisor | Notes |
|---|---|---|---|---|
| PoreVolume | Volume (pL) | Volume | 1000 | C++ um^3 -> MATLAB pL |
| PoreSurfaceArea | Surface Area (um2 / 1000) | SA | 1000 | |
| PoreCharacteristicLength | Characteristic Length (um) | CharacteristicLength | 1 | |
| PoreLongestLength | Longest Length (um) | LongestLength | 1 | |
| PoreAvgInternalDiam | Avg Internal Diam (um) | AvgInternalDiam | 1 | |
| PoreAspectRatio | Aspect Ratio | AspectRatio | 1 | |
| PoreNumHallways | # Hallways | NumHallways | 1 | |
| PoreNumCrawlSpaces | # Crawl Spaces | NumCrawlSpaces | 1 | |
| PoreNumConnectedPores | # Connected Pores | NumConnectedPores | 1 | |
| PoreNumSurroundingPores | # Surrounding Pores | NumSurroundingPores | 1 | |
| PoreNumEdges | # Particle Edges | NumEdges | 1 | Name differs |
| PoreNormalizedNeighbors | Normalized Neighbors | NormalizedNeighbors | 1 | |
| PoreNumPeaks | # Peaks | NumPeaks | 1 | |
| PoreNumSurrParticles | # Surrounding Particles | NumSurrParticles | 1 | |
| PoreLargestEnclosedSphere | Largest Enclosed Sphere Diameter(um) | LargestEnclosedSphereDiam | 1 | |
| PoreLargestDoorDiam | Largest Door Diameter (um) | LargestDoorDiam | 1 | |
| PoreSmallestDoorDiam | Smallest Door Diameter (um) | SmallestDoorDiam | 1 | |
| PoreEllipsoidAxis1 | Ellipsoid Axis 1 Length (um) | EllipsoidAxis1Length | 1 | |
| PoreEllipsoidAxis2 | Ellipsoid Axis 2 Length (um) | EllipsoidAxis2Length | 1 | |
| PoreEllipsoidAxis3 | Ellipsoid Axis 3 Length (um) | EllipsoidAxis3Length | 1 | |
| PoreEllipsoidClassification | Ellipsoid Classification | EllipsoidClassification | 1 | |
| PoreIsotropy | Isotropy | IsotropyAnisotropy | 1 | Name differs |
| PoreXCentroid | x Centroid | xCentroid | 1 | |
| PoreYCentroid | y Centroid | yCentroid | 1 | |
| PoreZCentroid | z Centroid | zCentroid | 1 | |

### Empty in C++ (5)

These exist in the C++ JSON schema but always have empty `values` arrays. They are populated in MATLAB.

| Key | MATLAB Name | C++ Name |
|---|---|---|
| PoreMeanLocalThickness | Mean Local Thickness (um) | MeanLocalThickness |
| PoreLigandConcentration | Ligand Concentration (umoles / L) | LigandConcentration |
| PoreAccessibleLigand | Accessible Ligand (umoles) | AccessibleLigand |
| PoreParticleSA | Particle Surface Area (um^2) | ParticleSA |
| PoreOpenSA | Open (Non-Particle) Surface Area (um^2) | OpenSA |

## Other Descriptors (26 total)

All are vector (one value per particle, door, or path). In the MATLAB Excel, these are columns 0-22 (before "Volume (pL)"). In C++ JSON, these are under `otherDescriptors`.

### Populated in Both Versions (6)

| Key | MATLAB Name | C++ Name | Notes |
|---|---|---|---|
| ParticleDiameter | Particle Diameter (um) | ParticleDiam | |
| ParticleCoordination | Particle Coordination # | ParticleCoord | |
| TouchingParticleCoord | Touching Particle Coord # | TouchingParticle | Name differs |
| ExitDoorDiameter | Exit Door Diameter (um) | ExitDoorDiam | |
| IntDoorDiameter | Internal Door Diameter (um) | IntDoorDiam | Empty in older API versions |
| CrawlSpaceWidth | Crawl Space Width (um) | CrawlSpaceWidth | Empty in older API versions |

### Empty in C++ (17)

These exist in the C++ JSON schema but always have empty `values` arrays.

| Key | MATLAB Name | C++ Name | Category |
|---|---|---|---|
| PathLength | Path Length (um) | PathLength | Path |
| TortuosityByLength | Tortuosity by Length | TortuositybyLength | Path |
| TortuosityByVolume | Tortuosity by Volume (pL) | TortuositybyVol | Path |
| NumIntPoresPath | # Interior 3D Pores Traversed by Path | NumIntPoresPath | Path |
| NumExtPoresPath | # Exterior 3D Pores Traversed by Path | NumExtPoresPath | Path |
| NumParticlesEnclosingIntPath | # Particles Enclosing Interior Path | NumParticlesEnclosingIntPath | Path |
| NumParticlesEnclosingExitPath | # Particles Enclosing Exiting Path | NumParticlesEnclosingExitPath | Path |
| NumBottlenecksTotal | # Bottlenecks (total) | NumBottlenecksTotal | Bottleneck |
| AvgBottleneckDiamTotal | Avg Bottleneck Diameter (total) (um) | AvgBottleneckDiamTotal | Bottleneck |
| NumBottlenecksDoors | # Bottlenecks (doors) | NumBottlenecksDoors | Bottleneck |
| AvgBottleneckDiamDoors | Avg Bottleneck Diameter (doors) (um) | AvgBottleneckDiamDoors | Bottleneck |
| SurfaceLigandConc | Surface Ligand Conc (umoles / um^2) | SurfaceLigandConc | Ligand |
| SurfaceAccessibleLigand | Surface Accessible Ligand (umoles) | SurfaceAccessibleLigand | Ligand |
| RegionsVol0 | Region Vols, <1 um (pL) | RegionsVol0 | Region |
| RegionsVol10 | Region Vols, 10 um (pL) | RegionsVol10 | Region |
| RegionsVol30 | Region Vols, 30 um (pL) | RegionsVol30 | Region |
| RegionsVol60 | Region Vols, 60 um (pL) | RegionsVol60 | Region |

### C++ Only (3)

These exist in C++ but have no MATLAB equivalent. They are not mapped.

| C++ Name | Group | Description |
|---|---|---|
| xParticleCOM | otherDescriptors | Particle center of mass (x) |
| yParticleCOM | otherDescriptors | Particle center of mass (y) |
| zParticleCOM | otherDescriptors | Particle center of mass (z) |

## Special Fields

| Field | Location | Purpose |
|---|---|---|
| IsInterior | C++ poreDescriptors | Boolean mask used to filter interior pores. Not a descriptor for comparison. |
| UniqueID | MATLAB Excel col 53 | Pore ID string. Not numeric, skipped by comparison. |
| DomainSize | C++ globalDescriptors | String like "602 x 602 x 600". Not numeric. |
