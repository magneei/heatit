"""Base entity for the Heatit WiFi integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HeatitDataUpdateCoordinator


class HeatitEntity(CoordinatorEntity[HeatitDataUpdateCoordinator]):
    """Base class for Heatit entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HeatitDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        info = coordinator.data.info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, info.mac_addr)},
            name=coordinator.data.config.display_name or info.device_type,
            manufacturer="Heatit",
            model=info.device_type,
            sw_version=info.sw_ver,
            hw_version=info.hw_ver,
            serial_number=info.serial_num,
        )
