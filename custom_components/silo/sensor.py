"""Sensors for a silo: how full it is, the grain's height, volume and weight, and the room left."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfMass, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SiloConfigEntry, SiloData
from .const import CONF_SOURCE, CONTENTS_KEYS, DOMAIN, SHAPE_KEYS
from .geometry import CUBIC_METRES, KILOGRAMS, METRES, Reading

LENGTHS = {
    "m": UnitOfLength.METERS,
    "cm": UnitOfLength.CENTIMETERS,
    "mm": UnitOfLength.MILLIMETERS,
    "ft": UnitOfLength.FEET,
    "in": UnitOfLength.INCHES,
}
VOLUMES = {"m3": UnitOfVolume.CUBIC_METERS, "L": UnitOfVolume.LITERS, "ft3": UnitOfVolume.CUBIC_FEET}
# Home Assistant has no tonnes or short tons: those weights go without a device class.
MASSES = {"kg": UnitOfMass.KILOGRAMS, "lb": UnitOfMass.POUNDS}


@dataclass(frozen=True, kw_only=True)
class SiloSensorDescription(SensorEntityDescription):
    value: Callable[[Reading, dict[str, Any]], float | None]
    # Whether the sensor needs a weight (a grain, a density or a capacity).
    needs_weight: bool = False


def _weight(kg: float | None, options: dict[str, Any]) -> float | None:
    return None if kg is None else kg / KILOGRAMS[options["weight_unit"]]


SENSORS = (
    SiloSensorDescription(
        key="fill",
        translation_key="fill",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value=lambda r, _: r.percent,
    ),
    SiloSensorDescription(
        key="level",
        translation_key="level",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda r, o: r.level / METRES[o["unit"]],
    ),
    SiloSensorDescription(
        key="rings",
        translation_key="rings",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value=lambda r, _: r.rings,
    ),
    SiloSensorDescription(
        key="volume",
        translation_key="volume",
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda r, o: r.volume / CUBIC_METRES[o["volume_unit"]],
    ),
    SiloSensorDescription(
        key="weight",
        translation_key="weight",
        state_class=SensorStateClass.MEASUREMENT,
        needs_weight=True,
        value=lambda r, o: _weight(r.weight, o),
    ),
    SiloSensorDescription(
        key="remaining",
        translation_key="remaining",
        state_class=SensorStateClass.MEASUREMENT,
        needs_weight=True,
        value=lambda r, o: _weight(r.remaining, o),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: SiloConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the silo's sensors; the weight ones only when the silo has a density."""
    data = entry.runtime_data
    has_weight = data.silo is not None and data.silo.density is not None
    async_add_entities(
        SiloSensor(hass, entry, description) for description in SENSORS if has_weight or not description.needs_weight
    )


class SiloSensor(SensorEntity):
    """One value of the silo, recomputed whenever its source sensor changes."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: SiloSensorDescription

    def __init__(self, hass: HomeAssistant, entry: SiloConfigEntry, description: SiloSensorDescription) -> None:
        self.entity_description = description
        self._data: SiloData = entry.runtime_data
        options = self._data.options
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        if description.key == "fill":
            self._attr_icon = "mdi:silo"
            # Static, and the card reads them from the live state: no need to fill the database.
            self._unrecorded_attributes = frozenset({"silo", "level", "source"})
        elif description.key == "level":
            self._attr_native_unit_of_measurement = LENGTHS[options["unit"]]
        elif description.key == "rings":
            self._attr_icon = "mdi:ladder"
        elif description.key == "volume":
            unit = options["volume_unit"]
            self._attr_native_unit_of_measurement = VOLUMES.get(unit, unit)
            if unit in VOLUMES:
                self._attr_device_class = SensorDeviceClass.VOLUME_STORAGE
        else:
            unit = options["weight_unit"]
            self._attr_native_unit_of_measurement = MASSES.get(unit, unit)
            self._attr_icon = "mdi:weight" if description.key == "weight" else "mdi:truck-delivery"
            if unit in MASSES:
                self._attr_device_class = SensorDeviceClass.WEIGHT
            else:
                self._attr_suggested_display_precision = 1

        # Shown in the unit chosen for the silo, not converted to the system's (a bin in inches, not in mm).
        if self.device_class is not None:
            self._attr_suggested_unit_of_measurement = self.native_unit_of_measurement

        # On the sensor's device (the ESPHome board, say), like the helpers built into Home Assistant;
        # a device of its own when the sensor has none.
        if (device := async_entity_id_to_device(hass, entry.options[CONF_SOURCE])) is not None:
            self.device_entry = device
        else:
            self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._data.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> float | None:
        reading = self._data.reading
        return None if reading is None else self.entity_description.value(reading, self._data.options)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """On the fill sensor, everything Silo Card needs to draw the silo: nothing to enter twice."""
        if self.entity_description.key != "fill":
            return None
        options = self._data.options
        silo = {key: options[key] for key in ("measure", "unit", *SHAPE_KEYS, *CONTENTS_KEYS) if key in options}
        reading = self._data.reading
        return {
            "source": self._data.source,
            "level": None if reading is None else round(reading.level, 4),
            "silo": silo,
        }
