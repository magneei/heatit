"""Sensor entities for the Heatit WiFi integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .heatit_api import HeatitDevice

from .const import DOMAIN
from .coordinator import HeatitDataUpdateCoordinator
from .entity import HeatitEntity


@dataclass(frozen=True, kw_only=True)
class HeatitSensorDescription(SensorEntityDescription):
    value_fn: Callable[[HeatitDevice], float | int | None]


SENSORS: tuple[HeatitSensorDescription, ...] = (
    HeatitSensorDescription(
        key="floor_temperature",
        translation_key="floor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.sensors.floor_temp if d.sensors else None,
    ),
    HeatitSensorDescription(
        key="room_temperature",
        translation_key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.sensors.room_temp if d.sensors else None,
    ),
    HeatitSensorDescription(
        key="external_temperature",
        translation_key="external_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.sensors.external_temp if d.sensors else None,
    ),
    HeatitSensorDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        value_fn=lambda d: d.sensors.rssi if d.sensors else None,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HeatitDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HeatitSensor(coordinator, desc) for desc in SENSORS
    )


class HeatitSensor(HeatitEntity, SensorEntity):
    """Sensor entity for a Heatit device."""

    entity_description: HeatitSensorDescription

    def __init__(
        self,
        coordinator: HeatitDataUpdateCoordinator,
        description: HeatitSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.data.info.mac_addr}_{description.key}"
        )

    @property
    def native_value(self) -> float | int | None:
        return self.entity_description.value_fn(self.coordinator.data)
