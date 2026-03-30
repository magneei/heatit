"""Data models for the Heatit WiFi thermostat API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum


class OperatingMode(IntEnum):
    HOME = 0
    AWAY = 1
    TIMEPLAN = 2
    ANTIFREEZE = 3
    ENERGY_MANAGEMENT = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


# deviceState is a bitmask: upper bits = opMode × 256, lower bits = heating activity
# Known values: 0=idle/home, 256=away, 512=timeplan, 768=antifreeze, 1024=energy_mgmt
# The relay_state field separately indicates if the relay is on/off.
def is_heating(device_state: int, relay_state: int) -> bool:
    """Determine if the device is actively heating."""
    return relay_state == 1


@dataclass
class DeviceInfo:
    """Device metadata from the device tree."""

    device_id: str
    device_type: str
    mac_addr: str
    serial_num: str
    online: bool
    sw_ver: str
    hw_ver: str
    zone_name: str = ""
    display_name: str = ""

    @classmethod
    def from_tree_node(cls, node: dict, zone_name: str = "") -> DeviceInfo:
        attrs = {a["key"]: a["value"] for a in node["i"].get("attr", [])}
        return cls(
            device_id=node["i"]["id"],
            device_type=attrs.get("devType", ""),
            mac_addr=attrs.get("macAddr", ""),
            serial_num=attrs.get("serialNum", ""),
            online=attrs.get("online", "false") == "true",
            sw_ver=attrs.get("swVer", ""),
            hw_ver=attrs.get("hwVer", ""),
            zone_name=zone_name,
        )


@dataclass
class DeviceConfig:
    """Device configuration from getDeviceState (reported shadow)."""

    device_id: str
    set_point: float  # °C
    current_set_point: float  # °C
    away_set_point: float  # °C
    op_mode: OperatingMode
    temp_unit: int  # 0=C, 1=F
    display_name: str
    online: bool
    mac_addr: str
    serial_num: str
    sw_ver: str
    hw_ver: str
    error_codes: int
    status_codes: int
    version: int  # shadow version

    @classmethod
    def from_state_response(cls, data: dict) -> DeviceConfig:
        reported = json.loads(data["reported"])
        return cls(
            device_id=reported["deviceId"],
            set_point=reported.get("setPoint", 0) / 10.0,
            current_set_point=reported.get("currentSetPoint", 0) / 10.0,
            away_set_point=reported.get("awaySetPoint", 0) / 10.0,
            op_mode=OperatingMode(reported.get("opMode", 0)),
            temp_unit=reported.get("tempUnit", 0),
            display_name=reported.get("displayName", ""),
            online=reported.get("online", False),
            mac_addr=reported.get("macAddr", ""),
            serial_num=reported.get("serialNum", ""),
            sw_ver=reported.get("swVer", ""),
            hw_ver=reported.get("hwVer", ""),
            error_codes=reported.get("errorCodes", 0),
            status_codes=reported.get("statusCodes", 0),
            version=data.get("version", 0),
        )


@dataclass
class SensorData:
    """Live sensor readings from getLatestData."""

    device_id: str
    timestamp: int
    current_temp: float  # °C
    current_set_point: float  # °C
    floor_temp: float  # °C
    room_temp: float  # °C
    external_temp: float  # °C
    device_state: int  # 0=idle, 1=heating(?), 256=away(?)
    relay_state: int  # 0=off, 1=on
    relay_on_time: int
    rssi: int  # WiFi signal dBm

    @classmethod
    def from_data_response(cls, data: dict) -> SensorData:
        inner = json.loads(data["data"])
        return cls(
            device_id=data["deviceId"],
            timestamp=int(data.get("timestamp", 0)),
            current_temp=inner.get("currentTemp", 0) / 10.0,
            current_set_point=inner.get("currentSetPoint", 0) / 10.0,
            floor_temp=inner.get("floorSensTemp", 0) / 10.0,
            room_temp=inner.get("roomSensTemp", 0) / 10.0,
            external_temp=inner.get("espSensorTemp", 0) / 10.0,
            device_state=inner.get("deviceState", 0),
            relay_state=inner.get("relayState", 0),
            relay_on_time=inner.get("relayOnTime", 0),
            rssi=inner.get("rssi", 0),
        )


@dataclass
class HeatitDevice:
    """Combined device info, config, and sensor data."""

    info: DeviceInfo
    config: DeviceConfig | None = None
    sensors: SensorData | None = None
