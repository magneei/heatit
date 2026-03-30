"""Climate entity for the Heatit WiFi integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .heatit_api import OperatingMode

from .const import DOMAIN
from .coordinator import HeatitDataUpdateCoordinator
from .entity import HeatitEntity

PRESET_HOME = "Home"
PRESET_AWAY = "Away"
PRESET_TIMEPLAN = "Timeplan"
PRESET_ANTIFREEZE = "Antifreeze"
PRESET_ENERGY = "Energy Management"

MODE_TO_PRESET = {
    OperatingMode.HOME: PRESET_HOME,
    OperatingMode.AWAY: PRESET_AWAY,
    OperatingMode.TIMEPLAN: PRESET_TIMEPLAN,
    OperatingMode.ANTIFREEZE: PRESET_ANTIFREEZE,
    OperatingMode.ENERGY_MANAGEMENT: PRESET_ENERGY,
}

PRESET_TO_MODE = {v: k for k, v in MODE_TO_PRESET.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeatitDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HeatitClimate(coordinator)])


class HeatitClimate(HeatitEntity, ClimateEntity):
    """Climate entity for a Heatit WiFi thermostat."""

    _attr_name = None  # Use device name
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_preset_modes = list(MODE_TO_PRESET.values())
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_min_temp = 5.0
    _attr_max_temp = 40.0
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator: HeatitDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.info.mac_addr}_climate"

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        sensors = self.coordinator.data.sensors
        if sensors and sensors.relay_state == 1:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def current_temperature(self) -> float | None:
        sensors = self.coordinator.data.sensors
        return sensors.floor_temp if sensors else None

    @property
    def target_temperature(self) -> float | None:
        config = self.coordinator.data.config
        if not config:
            return None
        if config.op_mode == OperatingMode.AWAY:
            return config.away_set_point
        return config.set_point

    @property
    def preset_mode(self) -> str | None:
        config = self.coordinator.data.config
        if not config:
            return None
        return MODE_TO_PRESET.get(config.op_mode, PRESET_HOME)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get("temperature")
        if temp is not None:
            await self.coordinator.client.async_set_temperature(
                self.coordinator.device_id, temp
            )
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # Only HEAT is supported; nothing to do
        pass

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode = PRESET_TO_MODE.get(preset_mode)
        if mode is not None:
            await self.coordinator.client.async_set_mode(
                self.coordinator.device_id, mode
            )
            await self.coordinator.async_request_refresh()
