"""Binary sensor entities for the Heatit WiFi integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HeatitDataUpdateCoordinator
from .entity import HeatitEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeatitDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HeatitHeatingBinarySensor(coordinator)])


class HeatitHeatingBinarySensor(HeatitEntity, BinarySensorEntity):
    """Binary sensor indicating whether the thermostat is actively heating."""

    _attr_name = "Heating"
    _attr_device_class = BinarySensorDeviceClass.HEAT

    def __init__(self, coordinator: HeatitDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.data.info.mac_addr}_heating"
        )

    @property
    def is_on(self) -> bool | None:
        sensors = self.coordinator.data.sensors
        if sensors is None:
            return None
        return sensors.relay_state == 1
