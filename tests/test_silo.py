"""Tests for the Silo integration: flows, sensors, the card's attributes and the translations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.silo.const import DOMAIN

INTEGRATION = Path(__file__).parent.parent / "custom_components" / DOMAIN
SOURCE = "sensor.soue1ben2_distance"
INCH = 0.0254

# The maintainer's feed bin, as the flow stores it.
BIN = {
    "source": SOURCE,
    "measure": "distance",
    "unit": "in",
    "shape": "round",
    "diameter": 108,
    "rings": 7,
    "ring_height": 32,
    "top": "cone",
    "top_height": 24,
    "bottom": "cone",
    "bottom_height": 84,
    "outlet": 0,
    "capacity": 24,
    "density_unit": "kg/m3",
    "weight_unit": "ton",
    "volume_unit": "bu",
    "include_roof": False,
}
HEIGHT = (84 + 7 * 32 + 24) * INCH


def _distance(hass: HomeAssistant, metres: float | str, unit: str = "m") -> None:
    hass.states.async_set(SOURCE, str(metres), {"unit_of_measurement": unit, "device_class": "distance"})


async def _setup(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Soue 1 Ben 2", data={}, options=options or BIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, entry: MockConfigEntry, key: str):
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{key}")
    return hass.states.get(entity_id) if entity_id else None


# ---------- config flow ----------


async def test_flow_creates_a_silo_named_after_the_sensors_device(hass: HomeAssistant) -> None:
    device_registry, entity_registry = dr.async_get(hass), er.async_get(hass)
    esphome = MockConfigEntry(domain="esphome")
    esphome.add_to_hass(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=esphome.entry_id, identifiers={("esphome", "soue1ben2")}, name="Soue 1 Ben 2"
    )
    entity_registry.async_get_or_create(
        "sensor", "esphome", "distance", suggested_object_id="soue1ben2_distance", device_id=device.id
    )
    _distance(hass, 3)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"source": SOURCE, "measure": "distance", "unit": "in"}
    )
    assert result["step_id"] == "shape"
    assert result["description_placeholders"] == {"unit": "in"}

    shape = {k: BIN[k] for k in ("shape", "diameter", "rings", "ring_height", "top", "top_height", "bottom")}
    # A cone bottom needs its height.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**shape, "bottom_height": 0, "outlet": 0}
    )
    assert result["errors"] == {"bottom_height": "hopper_height"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**shape, "rings": 7.0, "bottom_height": 84, "outlet": 0}
    )
    assert result["step_id"] == "contents"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "grain": "none",
            "capacity": 24,
            "density_unit": "kg/m3",
            "weight_unit": "ton",
            "volume_unit": "l",
            "include_roof": False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Soue 1 Ben 2"
    options = result["options"]
    assert options["rings"] == 7 and isinstance(options["rings"], int)
    assert options["volume_unit"] == "L"
    assert "grain" not in options
    assert "density" not in options
    await hass.async_block_till_done()

    # Its sensors sit on the ESPHome device, next to the distance they come from.
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    fill = entity_registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_fill")
    assert entity_registry.async_get(fill).device_id == device.id


async def test_flow_refuses_a_sensor_that_already_has_a_silo(hass: HomeAssistant) -> None:
    await _setup(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"source": SOURCE, "measure": "distance", "unit": "m"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_names_a_silo_without_a_device_after_the_sensor(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.bin_3", "2.0", {"friendly_name": "Bin 3 distance", "unit_of_measurement": "m"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"source": "sensor.bin_3", "measure": "distance", "unit": "m"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "shape": "round",
            "diameter": 0,
            "rings": 8,
            "ring_height": 0.8,
            "top": "cone",
            "top_height": 0,
            "bottom": "flat",
            "bottom_height": 0,
            "outlet": 0,
        },
    )
    assert result["errors"] == {"diameter": "positive", "top_height": "roof_height"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "shape": "round",
            "diameter": 8.2,
            "rings": 8,
            "ring_height": 0.8,
            "top": "flat",
            "top_height": 0,
            "bottom": "flat",
            "bottom_height": 0,
            "outlet": 0,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "grain": "corn",
            "density_unit": "kg/m3",
            "weight_unit": "t",
            "volume_unit": "m3",
            "include_roof": False,
        },
    )
    assert result["title"] == "Bin 3 distance"
    assert result["options"]["grain"] == "corn"


async def test_options_convert_the_lengths_to_a_new_unit(hass: HomeAssistant) -> None:
    _distance(hass, 3)
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"source": SOURCE, "measure": "distance", "unit": "ft"}
    )
    assert result["step_id"] == "shape"
    defaults = {str(key): key.default() for key in result["data_schema"].schema if callable(key.default)}
    assert defaults["diameter"] == 9
    assert defaults["bottom_height"] == 7
    assert defaults["ring_height"] == 2.67
    result = await hass.config_entries.options.async_configure(result["flow_id"], {**defaults})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "grain": "none",
            "capacity": 24,
            "density_unit": "kg/m3",
            "weight_unit": "ton",
            "volume_unit": "bu",
            "include_roof": False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["unit"] == "ft"
    assert entry.options["diameter"] == 9


async def test_flow_keeps_each_lengths_own_unit(hass: HomeAssistant) -> None:
    _distance(hass, 3)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"source": SOURCE, "measure": "distance", "unit": "ft"}
    )
    # As the manufacturer gives it: feet, except the rings, in inches.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "shape": "round",
            "diameter": 9,
            "diameter_unit": "ft",
            "rings": 7,
            "ring_height": 32,
            "ring_height_unit": "in",
            "top": "cone",
            "top_height": 2,
            "top_height_unit": "ft",
            "bottom": "cone",
            "bottom_height": 7,
            "bottom_height_unit": "ft",
            "outlet": 0,
            "outlet_unit": "ft",
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "grain": "none",
            "capacity": 24,
            "density_unit": "kg/m3",
            "weight_unit": "ton",
            "volume_unit": "bu",
            "include_roof": False,
        },
    )
    options = result["options"]
    assert options["ring_height_unit"] == "in"
    assert "diameter_unit" not in options
    assert "outlet_unit" not in options
    await hass.async_block_till_done()

    # The same bin as entered all in inches, so the same weight.
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    _distance(hass, HEIGHT - (84 + 4.5 * 32) * INCH)
    await hass.async_block_till_done()
    assert float(_state(hass, entry, "weight").state) == pytest.approx(16.4, abs=0.05)
    assert _state(hass, entry, "fill").attributes["silo"]["ring_height_unit"] == "in"


async def test_options_leave_lengths_with_their_own_unit(hass: HomeAssistant) -> None:
    _distance(hass, 3)
    entry = await _setup(
        hass, {**BIN, "unit": "ft", "diameter": 9, "ring_height_unit": "in", "top_height": 2, "bottom_height": 7}
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"source": SOURCE, "measure": "distance", "unit": "m"}
    )
    defaults = {str(key): key.default() for key in result["data_schema"].schema if callable(key.default)}
    assert defaults["diameter"] == 2.743  # followed the default unit: converted
    assert defaults["ring_height"] == 32  # in inches of its own: unchanged
    assert defaults["ring_height_unit"] == "in"
    assert defaults["diameter_unit"] == "m"


# ---------- sensors ----------


async def test_sensors_follow_the_distance(hass: HomeAssistant) -> None:
    _distance(hass, HEIGHT - (84 + 4.5 * 32) * INCH)
    entry = await _setup(hass)

    assert float(_state(hass, entry, "rings").state) == pytest.approx(4.5)
    assert float(_state(hass, entry, "level").state) == pytest.approx(84 + 4.5 * 32)
    assert _state(hass, entry, "level").attributes["unit_of_measurement"] == "in"
    weight = _state(hass, entry, "weight")
    assert float(weight.state) == pytest.approx(16.4, abs=0.05)
    assert weight.attributes["unit_of_measurement"] == "ton"
    assert float(_state(hass, entry, "remaining").state) == pytest.approx(24 - float(weight.state))
    assert _state(hass, entry, "volume").attributes["unit_of_measurement"] == "bu"

    # The sensor reports in millimetres now; empty bin.
    _distance(hass, HEIGHT * 1000 + 100, "mm")
    await hass.async_block_till_done()
    assert float(_state(hass, entry, "fill").state) == 0
    assert float(_state(hass, entry, "remaining").state) == pytest.approx(24)


async def test_fill_sensor_carries_the_silo_for_the_card(hass: HomeAssistant) -> None:
    _distance(hass, 2)
    entry = await _setup(hass)
    fill = _state(hass, entry, "fill")
    assert fill.attributes["source"] == SOURCE
    assert fill.attributes["level"] == pytest.approx(HEIGHT - 2, abs=1e-3)
    silo = fill.attributes["silo"]
    assert silo["diameter"] == 108
    assert silo["bottom"] == "cone"
    assert silo["unit"] == "in"
    assert "source" not in silo

    # No reading: the fill is unknown, but the card still gets the silo to draw.
    _distance(hass, "unavailable")
    await hass.async_block_till_done()
    fill = _state(hass, entry, "fill")
    assert fill.state == "unknown"
    assert fill.attributes["level"] is None
    assert fill.attributes["silo"]["rings"] == 7


async def test_no_weight_sensors_without_a_density(hass: HomeAssistant) -> None:
    _distance(hass, 2)
    options = {k: v for k, v in BIN.items() if k != "capacity"}
    entry = await _setup(hass, options)
    assert _state(hass, entry, "weight") is None
    assert _state(hass, entry, "remaining") is None
    assert _state(hass, entry, "volume") is not None


async def test_unload(hass: HomeAssistant) -> None:
    _distance(hass, 2)
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    _distance(hass, 1)
    await hass.async_block_till_done()


# ---------- translations ----------


def test_translations_match_strings() -> None:
    """en.json is a copy of strings.json, and fr.json has exactly the same keys."""

    def keys(node, path=""):
        if isinstance(node, dict):
            return {k for key, value in node.items() for k in keys(value, f"{path}.{key}")}
        return {path}

    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    for language in ("en", "fr"):
        translation = json.loads((INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8"))
        assert keys(translation) == keys(strings), language
    assert json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")) == strings
