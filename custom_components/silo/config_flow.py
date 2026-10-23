"""Config and options flows for Silo: the sensor, then the silo's shape, then what it holds."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    BOTTOMS,
    CAPACITY_PER,
    CONF_SOURCE,
    CONTENTS_KEYS,
    DEFAULTS,
    DENSITY_UNITS,
    DOMAIN,
    LENGTH_KEYS,
    LENGTH_UNITS,
    MEASURES,
    SHAPE_KEYS,
    SHAPES,
    TOPS,
    VOLUME_UNITS,
    WEIGHT_UNITS,
)
from .geometry import GRAINS, convert_length

CONF_NAME = "name"
NO_GRAIN = "none"

# Translation keys are lowercase: litres are "l" in the form and "L" (Silo Card's name) once stored.
FORM_VOLUME = {"L": "l"}
STORED_VOLUME = {v: k for k, v in FORM_VOLUME.items()}
# Density units are symbols, the same in every language.
DENSITY_LABELS = {"kg/m3": "kg/m³", "kg/hL": "kg/hL", "lb/bu": "lb/bu", "lb/ft3": "lb/ft³"}

# Number boxes step by what makes sense for the unit.
LENGTH_STEP = {"m": 0.01, "cm": 1, "ft": 0.01, "in": 0.5}


def _select(options: tuple[str, ...] | list[str], key: str, mode=SelectSelectorMode.DROPDOWN) -> SelectSelector:
    return SelectSelector(SelectSelectorConfig(options=list(options), mode=mode, translation_key=key))


def _length(unit: str) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(min=0, step=LENGTH_STEP[unit], mode=NumberSelectorMode.BOX, unit_of_measurement=unit)
    )


def _optional(key: str, values: dict[str, Any]) -> vol.Optional:
    """An optional field, prefilled only when it has a value (an empty number box stays empty)."""
    if values.get(key) is None:
        return vol.Optional(key)
    return vol.Optional(key, description={"suggested_value": values[key]})


def _sensor_schema(values: dict[str, Any], with_name: bool) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if with_name:
        fields[_optional(CONF_NAME, values)] = TextSelector()
    fields[vol.Required(CONF_SOURCE, default=values.get(CONF_SOURCE, vol.UNDEFINED))] = EntitySelector(
        EntitySelectorConfig(domain=["sensor", "input_number", "number"])
    )
    fields[vol.Required("measure", default=values["measure"])] = _select(MEASURES, "measure", SelectSelectorMode.LIST)
    fields[vol.Required("unit", default=values["unit"])] = _select(LENGTH_UNITS, "unit")
    return vol.Schema(fields)


def _shape_schema(values: dict[str, Any]) -> vol.Schema:
    length = _length(values["unit"])
    fields: dict[Any, Any] = {
        vol.Required("shape", default=values["shape"]): _select(SHAPES, "shape"),
        vol.Required("diameter", default=values.get("diameter", vol.UNDEFINED)): length,
        vol.Required("rings", default=values["rings"]): NumberSelector(
            NumberSelectorConfig(min=1, max=30, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Required("ring_height", default=values.get("ring_height", vol.UNDEFINED)): length,
        vol.Required("top", default=values["top"]): _select(TOPS, "top"),
        vol.Required("top_height", default=values["top_height"]): length,
        vol.Required("bottom", default=values["bottom"]): _select(BOTTOMS, "bottom"),
        vol.Required("bottom_height", default=values["bottom_height"]): length,
        vol.Required("outlet", default=values["outlet"]): length,
    }
    if values["measure"] == "distance":
        fields[_optional("sensor_height", values)] = length
    return vol.Schema(fields)


def _contents_schema(values: dict[str, Any]) -> vol.Schema:
    number = NumberSelector(NumberSelectorConfig(min=0, step=0.1, mode=NumberSelectorMode.BOX))
    return vol.Schema(
        {
            vol.Required("grain", default=values.get("grain") or NO_GRAIN): _select([NO_GRAIN, *GRAINS], "grain"),
            _optional("density", values): number,
            vol.Required("density_unit", default=values["density_unit"]): SelectSelector(
                SelectSelectorConfig(
                    options=[SelectOptionDict(value=u, label=DENSITY_LABELS[u]) for u in DENSITY_UNITS],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            _optional("capacity", values): number,
            vol.Required("capacity_per", default=values["capacity_per"]): _select(
                CAPACITY_PER, "capacity_per", SelectSelectorMode.LIST
            ),
            vol.Required("weight_unit", default=values["weight_unit"]): _select(WEIGHT_UNITS, "weight_unit"),
            vol.Required("volume_unit", default=FORM_VOLUME.get(values["volume_unit"], values["volume_unit"])): _select(
                [FORM_VOLUME.get(u, u) for u in VOLUME_UNITS], "volume_unit"
            ),
            vol.Required("include_roof", default=values["include_roof"]): BooleanSelector(),
        }
    )


def _shape_errors(values: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    for key in ("diameter", "ring_height"):
        if not values.get(key):
            errors[key] = "positive"
    if values["top"] != "flat" and not values.get("top_height"):
        errors["top_height"] = "roof_height"
    if values["bottom"] == "cone" and not values.get("bottom_height"):
        errors["bottom_height"] = "hopper_height"
    return errors


def _clean(values: dict[str, Any]) -> dict[str, Any]:
    """The options to store: whole rings, no grain called "none", nothing that doesn't apply."""
    options = {k: v for k, v in values.items() if k != CONF_NAME and v is not None}
    options["rings"] = int(options.get("rings", 1))
    options["volume_unit"] = STORED_VOLUME.get(options["volume_unit"], options["volume_unit"])
    if options.get("grain") == NO_GRAIN:
        options.pop("grain")
    for key in ("density", "capacity", "sensor_height"):
        if not options.get(key):
            options.pop(key, None)
    if "capacity" not in options:
        options.pop("capacity_per", None)
    if options.get("top") == "flat":
        options["top_height"] = 0
    if options.get("bottom") != "cone":
        options["bottom_height"] = options["outlet"] = 0
    if options.get("measure") != "distance":
        options.pop("sensor_height", None)
    return options


class _SiloSteps:
    """The three steps, shared by the config flow and the options flow."""

    _values: dict[str, Any]

    def _show(self, step_id: str, schema: vol.Schema, errors: dict[str, str] | None = None) -> ConfigFlowResult:
        return self.async_show_form(  # type: ignore[attr-defined]
            step_id=step_id,
            data_schema=schema,
            errors=errors or {},
            description_placeholders={"unit": self._values["unit"]},
        )

    def _set_sensor(self, user_input: dict[str, Any]) -> None:
        """Keep the sensor step's answers; a new unit converts the lengths already entered."""
        before = self._values["unit"]
        self._values.update(user_input)
        if user_input["unit"] != before:
            for key in LENGTH_KEYS:
                if isinstance(self._values.get(key), int | float):
                    self._values[key] = convert_length(self._values[key], before, user_input["unit"])

    async def async_step_shape(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            # An emptied optional box is missing from the input: forget the old value.
            self._values = {k: v for k, v in self._values.items() if k not in SHAPE_KEYS} | user_input
            errors = _shape_errors(self._values)
            if not errors:
                return await self.async_step_contents()
        return self._show("shape", _shape_schema(self._values), errors)

    async def async_step_contents(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._values = {k: v for k, v in self._values.items() if k not in CONTENTS_KEYS} | user_input
            return self._finish(_clean(self._values))
        return self._show("contents", _contents_schema(self._values))

    def _finish(self, options: dict[str, Any]) -> ConfigFlowResult:
        raise NotImplementedError


class SiloConfigFlow(_SiloSteps, ConfigFlow, domain=DOMAIN):
    """Add a silo: one entry for each silo and its sensor."""

    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._values = dict(DEFAULTS)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            if any(e.options.get(CONF_SOURCE) == user_input[CONF_SOURCE] for e in self._async_current_entries()):
                return self.async_abort(reason="already_configured")
            self._set_sensor(user_input)
            return await self.async_step_shape()
        return self._show("user", _sensor_schema(self._values, with_name=True))

    def _finish(self, options: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(title=self._title(), data={}, options=options)

    def _title(self) -> str:
        """The name given, else the sensor's device name, else the sensor's name."""
        if name := (self._values.get(CONF_NAME) or "").strip():
            return name
        source = self._values[CONF_SOURCE]
        entity = er.async_get(self.hass).async_get(source)
        if entity and entity.device_id and (device := dr.async_get(self.hass).async_get(entity.device_id)):
            return device.name_by_user or device.name or source
        state = self.hass.states.get(source)
        return state.name if state else source

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SiloOptionsFlow:
        return SiloOptionsFlow()


class SiloOptionsFlow(_SiloSteps, OptionsFlow):
    """Change the sensor, the shape or the contents; the sensors keep their IDs."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._set_sensor(user_input)
            return await self.async_step_shape()
        self._values = {**DEFAULTS, **self.config_entry.options}
        return self._show("init", _sensor_schema(self._values, with_name=False))

    def _finish(self, options: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(data=options)
