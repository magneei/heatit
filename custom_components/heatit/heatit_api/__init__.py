"""Heatit WiFi thermostat API client library."""

from .client import HeatitClient
from .exceptions import (
    HeatitAuthError,
    HeatitConnectionError,
    HeatitError,
    HeatitResponseError,
)
from .models import (
    DeviceConfig,
    DeviceInfo,
    HeatitDevice,
    OperatingMode,
    SensorData,
)

__all__ = [
    "HeatitClient",
    "HeatitError",
    "HeatitAuthError",
    "HeatitConnectionError",
    "HeatitResponseError",
    "DeviceConfig",
    "DeviceInfo",
    "HeatitDevice",
    "OperatingMode",
    "SensorData",
]
