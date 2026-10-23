"""Geometry tests: the same cases, and the same numbers, as Silo Card's tests/geometry.test.ts and silo.test.ts."""

from __future__ import annotations

import math

import pytest

from custom_components.silo.geometry import (
    KILOGRAMS,
    build_parts,
    convert_length,
    part_volume,
    read_silo,
    sensor_metres,
    silo_from_options,
    volume_below,
)

BASE = {
    "diameter": 2.0,
    "rings": 1,
    "ring_height": 3.0,
    "top": "flat",
    "top_height": 0.0,
    "bottom": "flat",
    "bottom_height": 0.0,
    "outlet": 0.0,
}
CYLINDER = math.pi * 3  # r = 1, h = 3

# The maintainer's feed bin: 9 ft wide, a 7 ft hopper, seven 32 in rings, a 2 ft roof, 24 short tons.
BIN = {
    "unit": "in",
    "diameter": 108,
    "rings": 7,
    "ring_height": 32,
    "top": "cone",
    "top_height": 24,
    "bottom": "cone",
    "bottom_height": 84,
    "capacity": 24,
    "weight_unit": "ton",
}
INCH = 0.0254
TON = KILOGRAMS["ton"]


def test_parts_stack_bottom_rings_top() -> None:
    parts = build_parts(
        **{**BASE, "rings": 3, "ring_height": 1, "bottom": "cone", "bottom_height": 2, "top": "cone", "top_height": 0.5}
    )
    assert [(p.kind, p.index) for p in parts] == [("bottom", 0), ("ring", 1), ("ring", 2), ("ring", 3), ("top", 0)]
    assert [p.z0 for p in parts] == [0, 2, 3, 4, 5]
    assert parts[-1].z1 == 5.5
    assert [p.kind for p in build_parts(**BASE)] == ["ring"]


def test_volumes_match_the_textbook() -> None:
    (ring,) = build_parts(**BASE)
    assert part_volume(ring, "round") == pytest.approx(CYLINDER)
    assert part_volume(ring, "square") == pytest.approx(12)
    (cone,) = build_parts(**{**BASE, "bottom": "cone", "bottom_height": 3})[:1]
    assert part_volume(cone, "round") == pytest.approx(CYLINDER / 3)
    dome = build_parts(**{**BASE, "top": "dome", "top_height": 3})[1]
    assert part_volume(dome, "round") == pytest.approx(2 / 3 * CYLINDER)
    hopper = build_parts(**{**BASE, "bottom": "cone", "bottom_height": 3, "outlet": 0.5})[0]
    assert part_volume(hopper, "round") == pytest.approx(math.pi * (1 + 0.25 + 0.0625))


def test_pointed_hopper_fills_as_the_cube_of_the_height() -> None:
    parts = build_parts(**{**BASE, "bottom": "cone", "bottom_height": 2})
    hopper = part_volume(parts[0], "round")
    for y in (0.3, 1, 1.7):
        assert volume_below(parts, "round", y) / hopper == pytest.approx((y / 2) ** 3)


def test_dome_fills_as_an_ellipsoid() -> None:
    parts = build_parts(**{**BASE, "top": "dome", "top_height": 1})
    assert volume_below(parts, "round", 3.5) - CYLINDER == pytest.approx(11 / 16 * 2 / 3 * math.pi)
    assert volume_below(parts, "round", 99) == pytest.approx(CYLINDER + 2 / 3 * math.pi)


def test_silo_needs_a_diameter_and_a_ring_height() -> None:
    assert silo_from_options({}) is None
    assert silo_from_options({"diameter": 3}) is None
    assert silo_from_options({"diameter": 3, "ring_height": 5}) is not None


def test_density_from_capacity_then_density_then_grain() -> None:
    metric = {"diameter": 2, "ring_height": 3, "top": "flat"}
    assert silo_from_options(metric).density is None
    assert silo_from_options({**metric, "grain": "wheat"}).density == pytest.approx(772.31, abs=0.05)
    assert silo_from_options({**metric, "grain": "wheat", "density": 75, "density_unit": "kg/hL"}).density == 750
    assert silo_from_options({**metric, "density": 700, "capacity": 6}).density == pytest.approx(6000 / CYLINDER)


def test_bin_reads_like_the_esphome_lambdas() -> None:
    silo = silo_from_options(BIN)
    height = (84 + 7 * 32 + 24) * INCH
    assert silo.height == pytest.approx(height)
    assert silo.sensor_height == pytest.approx(height)

    r = read_silo(silo, 2, "distance")
    assert r.level == pytest.approx(height - 2)
    assert read_silo(silo, 99, "distance").level == 0
    assert read_silo(silo, -1, "distance").level == pytest.approx(height)

    full = read_silo(silo, (84 + 7 * 32) * INCH, "level")
    assert full.percent == pytest.approx(100)
    assert full.weight / TON == pytest.approx(24)
    assert full.remaining == pytest.approx(0, abs=1e-6)
    assert full.rings == pytest.approx(7)

    # 4.5 rings: ESPHome said 4.5 × 3 + 3 = 16.5 tons; the true hopper volume makes it a little less.
    half = read_silo(silo, (84 + 4.5 * 32) * INCH, "level")
    assert half.rings == pytest.approx(4.5)
    assert half.weight / TON == pytest.approx(16.4, abs=0.05)

    assert read_silo(silo, 0, "distance").percent > 100
    peaked = silo_from_options({**BIN, "include_roof": True})
    assert read_silo(peaked, 0, "distance").percent == pytest.approx(100)


def test_capacity_of_one_ring_works_out_the_hopper() -> None:
    """The manufacturer's "3 tons a ring": the 7 ft hopper holds 87.5 % of a 32 in ring, so 7 × 3 + 2.6 tons."""
    silo = silo_from_options({**BIN, "capacity": 3, "capacity_per": "ring"})
    hopper = 84 / 3 / 32
    assert hopper == pytest.approx(0.875)
    full = read_silo(silo, (84 + 7 * 32) * INCH, "level")
    assert full.weight / TON == pytest.approx(21 + 3 * hopper)
    assert full.percent == pytest.approx(100)
    assert read_silo(silo, 84 * INCH, "level").weight / TON == pytest.approx(3 * hopper)


def test_units() -> None:
    assert sensor_metres("3.5", "m", "ft") == 3.5
    assert sensor_metres("3500", "mm", "m") == 3.5
    assert sensor_metres("10", "ft", "m") == pytest.approx(3.048)
    assert sensor_metres("10", None, "ft") == pytest.approx(3.048)
    assert sensor_metres("unavailable", "m", "m") is None
    assert sensor_metres("3", "%", "m") is None
    assert convert_length(108, "in", "ft") == 9
    assert convert_length(9, "ft", "m") == 2.743
