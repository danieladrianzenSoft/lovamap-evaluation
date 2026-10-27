from dataclasses import dataclass
from typing import Literal, Sequence

DescriptorGroup = Literal["global", "pore", "other"]
DescriptorKind = Literal["scalar", "vector"]  # scalar = one value per file, vector = per pore/particle
DescriptorKey = str  # any key present in DESCRIPTORS

@dataclass
class DescriptorSpec:
    key: str               # internal key, e.g. "VFF" or "PoreVolume"
    group: DescriptorGroup # "global", "pore", or "other"
    kind: DescriptorKind   # "scalar" or "vector"
    matlab_name: str       # column header in Excel (None = not in MATLAB)
    cpp_name: str          # key in JSON (None = not in C++)
    cpp_divisor: float = 1 # divisor to apply to C++ value to match MATLAB units (default 1 = no change)

DESCRIPTORS: dict[str, DescriptorSpec] = {

    # ==========================================
    # GLOBAL DESCRIPTORS (scalar, one per file)
    # ==========================================

    "dx": DescriptorSpec(
        key="dx", group="global", kind="scalar",
        matlab_name="dx",
        cpp_name="Dx",
    ),
    "NumVoxels": DescriptorSpec(
        key="NumVoxels", group="global", kind="scalar",
        matlab_name="voxels",
        cpp_name="NumVoxels",
    ),
    "NumParticles": DescriptorSpec(
        key="NumParticles", group="global", kind="scalar",
        matlab_name="# Particles",
        cpp_name="NumParticles",
    ),
    "NumParticleContacts": DescriptorSpec(
        key="NumParticleContacts", group="global", kind="scalar",
        matlab_name="# Particle Contacts",
        cpp_name="NumParticleContacts",
    ),
    "VFF": DescriptorSpec(
        key="VFF", group="global", kind="scalar",
        matlab_name="Void Vol Fraction",
        cpp_name="VFF",
    ),
    "ParticlePackingFraction": DescriptorSpec(
        key="ParticlePackingFraction", group="global", kind="scalar",
        matlab_name="Particle Fraction",
        cpp_name="ParticlePackingFraction",
    ),
    "AvgVoidAreaFraction": DescriptorSpec(
        key="AvgVoidAreaFraction", group="global", kind="scalar",
        matlab_name="Void Area Fraction",
        cpp_name="AvgVoidAreaFraction",
    ),
    "VFFIntPores": DescriptorSpec(
        key="VFFIntPores", group="global", kind="scalar",
        matlab_name="Void Vol Fraction of Interior Pores",
        cpp_name="VFFIntPores",
    ),
    "NumPoresTotal": DescriptorSpec(
        key="NumPoresTotal", group="global", kind="scalar",
        matlab_name="# 3D Pores",
        cpp_name="NumTotalPores",
    ),
    "NumPoresInterior": DescriptorSpec(
        key="NumPoresInterior", group="global", kind="scalar",
        matlab_name="# Interior 3D Pores",
        cpp_name="NumIntPores",
    ),
    "NumIntPoresDivParticles": DescriptorSpec(
        key="NumIntPoresDivParticles", group="global", kind="scalar",
        matlab_name="# Int 3D-Pores / # Particles Surr Int Pores",
        cpp_name="NumIntPoresdivParticlesSurrIntPores",
    ),
    "NumExitDoors": DescriptorSpec(
        key="NumExitDoors", group="global", kind="scalar",
        matlab_name="# Exterior Doors",
        cpp_name="NumExitDoors",
    ),
    "NumIntDoors": DescriptorSpec(
        key="NumIntDoors", group="global", kind="scalar",
        matlab_name="# Interior Doors",
        cpp_name="NumIntDoors",
    ),
    "NumPaths": DescriptorSpec(
        key="NumPaths", group="global", kind="scalar",
        matlab_name="# Paths",
        cpp_name="NumPaths",
    ),
    "ParticleAdjMaxEig": DescriptorSpec(
        key="ParticleAdjMaxEig", group="global", kind="scalar",
        matlab_name="Particle Adj Max Eig",
        cpp_name="ParticleAdjacencyMatrixEigenvalue",
    ),
    "PeakAdjMaxEig": DescriptorSpec(
        key="PeakAdjMaxEig", group="global", kind="scalar",
        matlab_name="Peak Adj Max Eig",
        cpp_name="PeakAdjacencyMatrixEigenvalue",
    ),
    "PoreAdjMaxEig": DescriptorSpec(
        key="PoreAdjMaxEig", group="global", kind="scalar",
        matlab_name="Pore Adj Max Eig",
        cpp_name="PoreAdjacencyMatrixEigenvalue",
    ),
    "MaxNumPeaksEdgePore": DescriptorSpec(
        key="MaxNumPeaksEdgePore", group="global", kind="scalar",
        matlab_name="Max # Pks of Edge Pore",
        cpp_name="MaxNumPeaksAmongSurfacePores",
    ),
    "LigandHotspotsVolFrac": DescriptorSpec(
        key="LigandHotspotsVolFrac", group="global", kind="scalar",
        matlab_name="Ligand Hotspots Volume Fraction",
        cpp_name="LigandHotspotsVolFrac",
    ),
    "MaxNumEquidistantParticles": DescriptorSpec(
        key="MaxNumEquidistantParticles", group="global", kind="scalar",
        matlab_name="Max # Equidistant Particles",
        cpp_name="MaxNumEquidistantParticles",
    ),

    # ==========================================
    # PORE DESCRIPTORS (vector, one per pore)
    # In MATLAB Excel: columns starting at "Volume (pL)" (col 23+)
    # In C++ JSON: poreDescriptors section
    # ==========================================

    "PoreVolume": DescriptorSpec(
        key="PoreVolume", group="pore", kind="vector",
        matlab_name="Volume (pL)",
        cpp_name="Volume",
        cpp_divisor=1000,  # C++ is um^3, MATLAB is pL (1 pL = 1000 um^3)
    ),
    "PoreSurfaceArea": DescriptorSpec(
        key="PoreSurfaceArea", group="pore", kind="vector",
        matlab_name="Surface Area (um2 / 1000)",
        cpp_name="SA",
        cpp_divisor=1000,  # C++ is um^2, MATLAB header says "um2 / 1000"
    ),
    "PoreCharacteristicLength": DescriptorSpec(
        key="PoreCharacteristicLength", group="pore", kind="vector",
        matlab_name="Characteristic Length (um)",
        cpp_name="CharacteristicLength",
    ),
    "PoreLongestLength": DescriptorSpec(
        key="PoreLongestLength", group="pore", kind="vector",
        matlab_name="Longest Length (um)",
        cpp_name="LongestLength",
    ),
    "PoreAvgInternalDiam": DescriptorSpec(
        key="PoreAvgInternalDiam", group="pore", kind="vector",
        matlab_name="Avg Internal Diam (um)",
        cpp_name="AvgInternalDiam",
    ),
    "PoreAspectRatio": DescriptorSpec(
        key="PoreAspectRatio", group="pore", kind="vector",
        matlab_name="Aspect Ratio",
        cpp_name="AspectRatio",
    ),
    "PoreNumHallways": DescriptorSpec(
        key="PoreNumHallways", group="pore", kind="vector",
        matlab_name="# Hallways",
        cpp_name="NumHallways",
    ),
    "PoreNumCrawlSpaces": DescriptorSpec(
        key="PoreNumCrawlSpaces", group="pore", kind="vector",
        matlab_name="# Crawl Spaces",
        cpp_name="NumCrawlSpaces",
    ),
    "PoreNumConnectedPores": DescriptorSpec(
        key="PoreNumConnectedPores", group="pore", kind="vector",
        matlab_name="# Connected Pores",
        cpp_name="NumConnectedPores",
    ),
    "PoreNumSurroundingPores": DescriptorSpec(
        key="PoreNumSurroundingPores", group="pore", kind="vector",
        matlab_name="# Surrounding Pores",
        cpp_name="NumSurroundingPores",
    ),
    "PoreNumEdges": DescriptorSpec(
        key="PoreNumEdges", group="pore", kind="vector",
        matlab_name="# Particle Edges",   # MATLAB name differs
        cpp_name="NumEdges",               # C++ name differs
    ),
    "PoreNormalizedNeighbors": DescriptorSpec(
        key="PoreNormalizedNeighbors", group="pore", kind="vector",
        matlab_name="Normalized Neighbors",
        cpp_name="NormalizedNeighbors",
    ),
    "PoreNumPeaks": DescriptorSpec(
        key="PoreNumPeaks", group="pore", kind="vector",
        matlab_name="# Peaks",
        cpp_name="NumPeaks",
    ),
    "PoreNumSurrParticles": DescriptorSpec(
        key="PoreNumSurrParticles", group="pore", kind="vector",
        matlab_name="# Surrounding Particles",
        cpp_name="NumSurrParticles",
    ),
    "PoreLargestEnclosedSphere": DescriptorSpec(
        key="PoreLargestEnclosedSphere", group="pore", kind="vector",
        matlab_name="Largest Enclosed Sphere Diameter(um)",
        cpp_name="LargestEnclosedSphereDiam",
    ),
    "PoreLargestDoorDiam": DescriptorSpec(
        key="PoreLargestDoorDiam", group="pore", kind="vector",
        matlab_name="Largest Door Diameter (um)",
        cpp_name="LargestDoorDiam",
    ),
    "PoreSmallestDoorDiam": DescriptorSpec(
        key="PoreSmallestDoorDiam", group="pore", kind="vector",
        matlab_name="Smallest Door Diameter (um)",
        cpp_name="SmallestDoorDiam",
    ),
    "PoreEllipsoidAxis1": DescriptorSpec(
        key="PoreEllipsoidAxis1", group="pore", kind="vector",
        matlab_name="Ellipsoid Axis 1 Length (um)",
        cpp_name="EllipsoidAxis1Length",
    ),
    "PoreEllipsoidAxis2": DescriptorSpec(
        key="PoreEllipsoidAxis2", group="pore", kind="vector",
        matlab_name="Ellipsoid Axis 2 Length (um)",
        cpp_name="EllipsoidAxis2Length",
    ),
    "PoreEllipsoidAxis3": DescriptorSpec(
        key="PoreEllipsoidAxis3", group="pore", kind="vector",
        matlab_name="Ellipsoid Axis 3 Length (um)",
        cpp_name="EllipsoidAxis3Length",
    ),
    "PoreEllipsoidClassification": DescriptorSpec(
        key="PoreEllipsoidClassification", group="pore", kind="vector",
        matlab_name="Ellipsoid Classification",
        cpp_name="EllipsoidClassification",
    ),
    "PoreIsotropy": DescriptorSpec(
        key="PoreIsotropy", group="pore", kind="vector",
        matlab_name="Isotropy",           # MATLAB name differs
        cpp_name="IsotropyAnisotropy",    # C++ name differs
    ),
    "PoreXCentroid": DescriptorSpec(
        key="PoreXCentroid", group="pore", kind="vector",
        matlab_name="x Centroid",
        cpp_name="xCentroid",
    ),
    "PoreYCentroid": DescriptorSpec(
        key="PoreYCentroid", group="pore", kind="vector",
        matlab_name="y Centroid",
        cpp_name="yCentroid",
    ),
    "PoreZCentroid": DescriptorSpec(
        key="PoreZCentroid", group="pore", kind="vector",
        matlab_name="z Centroid",
        cpp_name="zCentroid",
    ),
    "PoreMeanLocalThickness": DescriptorSpec(
        key="PoreMeanLocalThickness", group="pore", kind="vector",
        matlab_name="Mean Local Thickness (um)",
        cpp_name="MeanLocalThickness",
    ),
    "PoreLigandConcentration": DescriptorSpec(
        key="PoreLigandConcentration", group="pore", kind="vector",
        matlab_name="Ligand Concentration (umoles / L)",
        cpp_name="LigandConcentration",
    ),
    "PoreAccessibleLigand": DescriptorSpec(
        key="PoreAccessibleLigand", group="pore", kind="vector",
        matlab_name="Accessible Ligand (umoles)",
        cpp_name="AccessibleLigand",
    ),
    "PoreParticleSA": DescriptorSpec(
        key="PoreParticleSA", group="pore", kind="vector",
        matlab_name="Particle Surface Area (um^2)",
        cpp_name="ParticleSA",
    ),
    "PoreOpenSA": DescriptorSpec(
        key="PoreOpenSA", group="pore", kind="vector",
        matlab_name="Open (Non-Particle) Surface Area (um^2)",
        cpp_name="OpenSA",
    ),

    # ==========================================
    # OTHER DESCRIPTORS (vector, one per particle/door/path)
    # In MATLAB Excel: columns before "Volume (pL)" (cols 0-22)
    # In C++ JSON: otherDescriptors section
    # ==========================================

    "ParticleDiameter": DescriptorSpec(
        key="ParticleDiameter", group="other", kind="vector",
        matlab_name="Particle Diameter (um)",
        cpp_name="ParticleDiam",
    ),
    "ParticleCoordination": DescriptorSpec(
        key="ParticleCoordination", group="other", kind="vector",
        matlab_name="Particle Coordination #",
        cpp_name="ParticleCoord",
    ),
    "TouchingParticleCoord": DescriptorSpec(
        key="TouchingParticleCoord", group="other", kind="vector",
        matlab_name="Touching Particle Coord #",
        cpp_name="TouchingParticle",         # C++ name differs
    ),
    "ExitDoorDiameter": DescriptorSpec(
        key="ExitDoorDiameter", group="other", kind="vector",
        matlab_name="Exit Door Diameter (um)",
        cpp_name="ExitDoorDiam",
    ),
    "IntDoorDiameter": DescriptorSpec(
        key="IntDoorDiameter", group="other", kind="vector",
        matlab_name="Internal Door Diameter (um)",
        cpp_name="IntDoorDiam",
    ),
    "CrawlSpaceWidth": DescriptorSpec(
        key="CrawlSpaceWidth", group="other", kind="vector",
        matlab_name="Crawl Space Width (um)",
        cpp_name="CrawlSpaceWidth",
    ),
    "PathLength": DescriptorSpec(
        key="PathLength", group="other", kind="vector",
        matlab_name="Path Length (um)",
        cpp_name="PathLength",
    ),
    "TortuosityByLength": DescriptorSpec(
        key="TortuosityByLength", group="other", kind="vector",
        matlab_name="Tortuosity by Length",
        cpp_name="TortuositybyLength",
    ),
    "TortuosityByVolume": DescriptorSpec(
        key="TortuosityByVolume", group="other", kind="vector",
        matlab_name="Tortuosity by Volume (pL)",
        cpp_name="TortuositybyVol",
    ),
    "NumIntPoresPath": DescriptorSpec(
        key="NumIntPoresPath", group="other", kind="vector",
        matlab_name="# Interior 3D Pores Traversed by Path",
        cpp_name="NumIntPoresPath",
    ),
    "NumExtPoresPath": DescriptorSpec(
        key="NumExtPoresPath", group="other", kind="vector",
        matlab_name="# Exterior 3D Pores Traversed by Path",
        cpp_name="NumExtPoresPath",
    ),
    "NumParticlesEnclosingIntPath": DescriptorSpec(
        key="NumParticlesEnclosingIntPath", group="other", kind="vector",
        matlab_name="# Particles Enclosing Interior Path",
        cpp_name="NumParticlesEnclosingIntPath",
    ),
    "NumParticlesEnclosingExitPath": DescriptorSpec(
        key="NumParticlesEnclosingExitPath", group="other", kind="vector",
        matlab_name="# Particles Enclosing Exiting Path",
        cpp_name="NumParticlesEnclosingExitPath",
    ),
    "NumBottlenecksTotal": DescriptorSpec(
        key="NumBottlenecksTotal", group="other", kind="vector",
        matlab_name="# Bottlenecks (total)",
        cpp_name="NumBottlenecksTotal",
    ),
    "AvgBottleneckDiamTotal": DescriptorSpec(
        key="AvgBottleneckDiamTotal", group="other", kind="vector",
        matlab_name="Avg Bottleneck Diameter (total) (um)",
        cpp_name="AvgBottleneckDiamTotal",
    ),
    "NumBottlenecksDoors": DescriptorSpec(
        key="NumBottlenecksDoors", group="other", kind="vector",
        matlab_name="# Bottlenecks (doors)",
        cpp_name="NumBottlenecksDoors",
    ),
    "AvgBottleneckDiamDoors": DescriptorSpec(
        key="AvgBottleneckDiamDoors", group="other", kind="vector",
        matlab_name="Avg Bottleneck Diameter (doors) (um)",
        cpp_name="AvgBottleneckDiamDoors",
    ),
    "SurfaceLigandConc": DescriptorSpec(
        key="SurfaceLigandConc", group="other", kind="vector",
        matlab_name="Surface Ligand Conc (\u00b5moles / \u00b5m^2)",
        cpp_name="SurfaceLigandConc",
    ),
    "SurfaceAccessibleLigand": DescriptorSpec(
        key="SurfaceAccessibleLigand", group="other", kind="vector",
        matlab_name="Surface Accessible Ligand (\u00b5moles)",
        cpp_name="SurfaceAccessibleLigand",
    ),
    "RegionsVol0": DescriptorSpec(
        key="RegionsVol0", group="other", kind="vector",
        matlab_name="Region Vols, <1 um (pL)",
        cpp_name="RegionsVol0",
    ),
    "RegionsVol10": DescriptorSpec(
        key="RegionsVol10", group="other", kind="vector",
        matlab_name="Region Vols, 10 um (pL)",
        cpp_name="RegionsVol10",
    ),
    "RegionsVol30": DescriptorSpec(
        key="RegionsVol30", group="other", kind="vector",
        matlab_name="Region Vols, 30 um (pL)",
        cpp_name="RegionsVol30",
    ),
    "RegionsVol60": DescriptorSpec(
        key="RegionsVol60", group="other", kind="vector",
        matlab_name="Region Vols, 60 um (pL)",
        cpp_name="RegionsVol60",
    ),
}

DESCRIPTOR_KEYS = tuple(DESCRIPTORS.keys())


def validate_descriptor_keys(keys: Sequence[str]) -> list[str]:
    invalid = [key for key in keys if key not in DESCRIPTORS]
    if invalid:
        raise ValueError(
            "Unknown descriptor keys: "
            + ", ".join(invalid)
            + ". Valid keys: "
            + ", ".join(DESCRIPTOR_KEYS)
        )
    return list(keys)
