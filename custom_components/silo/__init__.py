"""Silo: how full a grain silo or bin is, from a distance sensor at its top."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_SOURCE, DEFAULTS
from .geometry import Reading, Silo, read_silo, sensor_metres, silo_from_options

PLATFORMS = [Platform.SENSOR]

type SiloConfigEntry = ConfigEntry[SiloData]


class SiloData:
    """The silo of one entry, and its latest reading, shared by its sensors."""

    def __init__(self, hass: HomeAssistant, entry: SiloConfigEntry) -> None:
        self.hass = hass
        self.options: dict[str, Any] = {**DEFAULTS, **entry.options}
        self.source: str = entry.options[CONF_SOURCE]
        self.silo: Silo | None = silo_from_options(self.options)
        self.reading: Reading | None = None
        self._listeners: list[Callable[[], None]] = []

    @callback
    def async_start(self) -> Callable[[], None]:
        """Read the source sensor now and on every change; returns the function that stops."""
        self._update(self.hass.states.get(self.source))
        return async_track_state_change_event(self.hass, [self.source], self._changed)

    @callback
    def _changed(self, event: Event[EventStateChangedData]) -> None:
        self._update(event.data["new_state"])
        for listener in list(self._listeners):
            listener()

    def _update(self, state: State | None) -> None:
        value = (
            None
            if state is None
            else sensor_metres(state.state, state.attributes.get("unit_of_measurement"), self.options["unit"])
        )
        self.reading = (
            None if value is None or self.silo is None else read_silo(self.silo, value, self.options["measure"])
        )

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)


async def async_setup_entry(hass: HomeAssistant, entry: SiloConfigEntry) -> bool:
    """Set up a silo from a config entry."""
    data = SiloData(hass, entry)
    entry.runtime_data = data
    entry.async_on_unload(data.async_start())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SiloConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: SiloConfigEntry) -> None:
    """Reload when the silo or its sensor change."""
    await hass.config_entries.async_reload(entry.entry_id)
