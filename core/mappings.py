from dataclasses import dataclass
from typing import Literal

DescriptorGroup = Literal["global", "pore", "other"]
DescriptorKind = Literal["scalar", "vector"]  # scalar = one value per file, vector = per pore/particle

@dataclass
class DescriptorSpec:
    key: str               # internal key, e.g. "VFF" or "PoreVolume"
    group: DescriptorGroup # "global", "pore", or "other"
    kind: DescriptorKind   # "scalar" or "vector"
    matlab_name: str       # column header in Excel
    cpp_name: str          # key in JSON
    cpp_divisor: float = 1 # divisor to apply to C++ value to match MATLAB units (default 1 = no change)

DESCRIPTORS: dict[str, DescriptorSpec] = {
    # --- global descriptors ---
    "dx": DescriptorSpec(
        key="dx",
        group="global",
        kind="scalar",
        matlab_name="dx",
        cpp_name="Dx",
        cpp_divisor=1
    ),
    "NumParticles": DescriptorSpec(
        key="NumParticles",
        group="global",
        kind="scalar",
        matlab_name="# Particles",
        cpp_name="NumParticles",
        cpp_divisor=1
    ),
    "VFF": DescriptorSpec(
        key="VFF",
        group="global",
        kind="scalar",
        matlab_name="Void Vol Fraction",
        cpp_name="VFF",
        cpp_divisor=1
    ),
    "NumPoresTotal": DescriptorSpec(
        key="NumPoresTotal",
        group="global",
        kind="scalar",
        matlab_name="# 3D Pores",
        cpp_name="NumTotalPores",
        cpp_divisor=1
    ),
    # add others as needed...

    # --- pore-level vector descriptors ---
    "PoreVolume": DescriptorSpec(
        key="PoreVolume",
        group="pore",
        kind="vector",
        matlab_name="Volume (pL)",  # Excel header
        cpp_name="Volume",          # json["poreDescriptors"]["Volume"]["values"]
        cpp_divisor=1
    ),
    "PoreSurfaceArea": DescriptorSpec(
        key="PoreSurfaceArea",
        group="pore",
        kind="vector",
        matlab_name="Surface Area (um2 / 1000)",
        cpp_name="SA",
        cpp_divisor=1000
    ),
    "PoreAspectRatio": DescriptorSpec(
        key="PoreAspectRatio",
        group="pore",
        kind="vector",
        matlab_name="Aspect Ratio",
        cpp_name="AspectRatio",
        cpp_divisor=1
    ),
    "PoreLongestLength": DescriptorSpec(
        key="PoreLongestLength",
        group="pore",
        kind="vector",
        matlab_name="Longest Length (um)",
        cpp_name="LongestLength",
        cpp_divisor=1
    ),
    "PoreLargestEnclosedSphere": DescriptorSpec(
        key="LargestEnclosedSphere",
        group="pore",
        kind="vector",
        matlab_name="Largest Enclosed Sphere Diameter(um)",
        cpp_name="LargestEnclosedSphereDiam",
        cpp_divisor=1
    ),


    # --- "other" vector descriptors ---
    "ParticleDiameter": DescriptorSpec(
        key="ParticleDiameter",
        group="other",
        kind="vector",
        matlab_name="Particle Diameter (um)",
        cpp_name="ParticleDiam",
    ),
}