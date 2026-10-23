"""Silo geometry, volumes and weights.

The silo is a stack of parts, bottom to top, each one a frustum (cylinder, cone or truncated cone) or a dome.
Everything here is in metres, cubic metres and kilograms; units are converted only on the way in and out.

Mirrored in Silo Card's src/geometry.ts, src/silo.ts and src/units.ts: change one, change the other.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# ---------- units ----------

POUND = 0.45359237  # kg
FOOT = 0.3048  # m
# US (Winchester) bushel, 2150.42 cubic inches, the one grain is sold by in North America.
BUSHEL = 0.03523907016688  # m³

METRES = {"m": 1.0, "cm": 0.01, "ft": FOOT, "in": 0.0254}
CUBIC_METRES = {"m3": 1.0, "L": 0.001, "ft3": FOOT**3, "bu": BUSHEL}
# `ton` is the short ton (2000 lb); `t` the metric tonne.
KILOGRAMS = {"t": 1000.0, "kg": 1.0, "ton": 2000 * POUND, "lb": POUND}
KG_PER_M3 = {"kg/m3": 1.0, "kg/hL": 10.0, "lb/bu": POUND / BUSHEL, "lb/ft3": POUND / FOOT**3}

# Units a distance sensor may report in, as Home Assistant spells them.
SENSOR_METRES = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "in": 0.0254, "ft": FOOT, "yd": 0.9144}

# Standard bushel weights (lb per US bushel), the ones North American grain is bought and sold by.
GRAINS = {
    "wheat": 60,
    "corn": 56,
    "barley": 48,
    "oats": 32,
    "soybeans": 60,
    "canola": 50,
    "rye": 56,
    "peas": 60,
    "flax": 56,
    "sorghum": 56,
}


def sensor_metres(state: str, unit: Any, fallback: str) -> float | None:
    """A sensor's state in metres, from its unit (or `fallback` when it has none); None without a length."""
    try:
        value = float(state)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    factor = SENSOR_METRES.get(unit.strip()) if isinstance(unit, str) and unit else METRES.get(fallback)
    return None if factor is None else value * factor


def convert_length(value: float, from_unit: str, to_unit: str) -> float:
    """A length in another unit, rounded to what makes sense for that unit."""
    decimals = {"m": 3, "cm": 1, "ft": 2, "in": 1}[to_unit]
    return round(value * METRES[from_unit] / METRES[to_unit], decimals)


# ---------- shape ----------


@dataclass(frozen=True)
class Part:
    """One part of the silo: the bottom, a ring or the top, between heights z0 and z1."""

    kind: str  # bottom, ring, top
    index: int  # ring number from 1 at the bottom; 0 for the top and bottom
    profile: str  # frustum, dome
    z0: float
    z1: float
    w0: float  # width at z0
    w1: float  # width at z1 (a dome comes to a point)


def build_parts(
    *,
    diameter: float,
    rings: int,
    ring_height: float,
    top: str,
    top_height: float,
    bottom: str,
    bottom_height: float,
    outlet: float,
) -> list[Part]:
    """The parts from bottom to top. A flat top or bottom has no height, so no part."""
    parts: list[Part] = []
    z = 0.0
    if bottom == "cone" and bottom_height > 0:
        width = min(max(outlet, 0.0), diameter)
        parts.append(Part("bottom", 0, "frustum", 0.0, bottom_height, width, diameter))
        z = bottom_height
    for i in range(1, rings + 1):
        parts.append(Part("ring", i, "frustum", z, z + ring_height, diameter, diameter))
        z += ring_height
    if top != "flat" and top_height > 0:
        parts.append(Part("top", 0, "dome" if top == "dome" else "frustum", z, z + top_height, diameter, 0.0))
    return parts


def _area(shape: str, width: float) -> float:
    return math.pi * width * width / 4 if shape == "round" else width * width


def width_at(part: Part, z: float) -> float:
    """Width of the part at height z (clamped to the part)."""
    h = part.z1 - part.z0
    t = min(max((z - part.z0) / h, 0.0), 1.0) if h > 0 else 0.0
    if part.profile == "dome":
        return part.w0 * math.sqrt(1 - t * t)
    return part.w0 + (part.w1 - part.w0) * t


def part_volume_below(part: Part, shape: str, z: float) -> float:
    """Volume of the part below height z."""
    h = part.z1 - part.z0
    y = min(max(z - part.z0, 0.0), h)
    if y <= 0:
        return 0.0
    a0 = _area(shape, part.w0)
    if part.profile == "dome":
        # Half an ellipsoid (or its square cousin): the area shrinks as 1 - (y/h)².
        return a0 * (y - y**3 / (3 * h * h))
    # Frustum between two similar cross-sections.
    ay = _area(shape, width_at(part, z))
    return y / 3 * (a0 + ay + math.sqrt(a0 * ay))


def part_volume(part: Part, shape: str) -> float:
    return part_volume_below(part, shape, part.z1)


def volume_below(parts: list[Part], shape: str, z: float) -> float:
    return sum(part_volume_below(part, shape, z) for part in parts)


# ---------- a silo and its reading ----------


@dataclass(frozen=True)
class Silo:
    """A silo from the integration's options, in metres."""

    shape: str
    parts: list[Part]
    height: float
    sensor_height: float
    rings: int
    body_start: float
    ring_height: float
    # Volume when full (m³): to the eave, or to the peak with include_roof.
    capacity: float
    # Bulk density (kg/m³), when a grain, a density or a capacity is set.
    density: float | None


@dataclass(frozen=True)
class Reading:
    level: float  # grain height above the silo's lowest point (m)
    distance: float  # from the sensor down to the grain (m)
    volume: float  # m³
    percent: float  # of the capacity; above 100 when grain fills a roof that isn't part of "full"
    weight: float | None  # kg
    remaining: float | None  # kg
    rings: float  # rings filled, 0 to the number of rings


def silo_from_options(options: dict[str, Any]) -> Silo | None:
    """The silo the options describe, or None while a dimension it needs is missing."""
    m = METRES.get(options.get("unit", "m"), 1.0)

    def length(key: str) -> float:
        value = options.get(key)
        return float(value) * m if isinstance(value, int | float) and value > 0 else 0.0

    diameter, ring_height = length("diameter"), length("ring_height")
    if not diameter or not ring_height:
        return None
    rings = max(1, round(options.get("rings", 1)))
    bottom = options.get("bottom", "flat")
    shape = options.get("shape", "round")
    parts = build_parts(
        diameter=diameter,
        rings=rings,
        ring_height=ring_height,
        top=options.get("top", "cone"),
        top_height=length("top_height"),
        bottom=bottom,
        bottom_height=length("bottom_height"),
        outlet=length("outlet"),
    )
    height = parts[-1].z1
    include_roof = bool(options.get("include_roof", False))
    capacity = sum(part_volume(p, shape) for p in parts if include_roof or p.kind != "top")

    density: float | None = None
    if (cap := options.get("capacity")) and cap > 0:
        # The weight of the whole silo, or of one full ring: the hopper and roof then follow from their volume.
        ring = next(p for p in parts if p.kind == "ring")
        volume = part_volume(ring, shape) if options.get("capacity_per") == "ring" else capacity
        density = cap * KILOGRAMS.get(options.get("weight_unit", "t"), 1.0) / volume
    elif (value := options.get("density")) and value > 0:
        density = value * KG_PER_M3.get(options.get("density_unit", "kg/m3"), 1.0)
    elif (grain := options.get("grain")) in GRAINS:
        density = GRAINS[grain] * KG_PER_M3["lb/bu"]

    first_ring = next(p for p in parts if p.kind == "ring")
    return Silo(
        shape=shape,
        parts=parts,
        height=height,
        sensor_height=length("sensor_height") or height,
        rings=rings,
        body_start=first_ring.z0,
        ring_height=ring_height,
        capacity=capacity,
        density=density,
    )


def read_silo(silo: Silo, value: float, measure: str) -> Reading:
    """The fill for a sensor value in metres: a distance from the sensor down, or the grain height."""
    raw = value if measure == "level" else silo.sensor_height - value
    level = min(max(raw, 0.0), silo.height)
    volume = volume_below(silo.parts, silo.shape, level)
    weight = None if silo.density is None else volume * silo.density
    remaining = None if weight is None else max(silo.capacity * silo.density - weight, 0.0)
    return Reading(
        level=level,
        distance=max(silo.sensor_height - level, 0.0),
        volume=volume,
        percent=volume / silo.capacity * 100 if silo.capacity > 0 else 0.0,
        weight=weight,
        remaining=remaining,
        rings=min(max((level - silo.body_start) / silo.ring_height, 0.0), silo.rings),
    )
