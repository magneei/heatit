"""Async API client for the Heatit WiFi thermostat cloud."""

from __future__ import annotations

import json

import aiohttp

from .auth import CognitoAuth
from .exceptions import HeatitConnectionError, HeatitResponseError
from .models import (
    DeviceConfig,
    DeviceInfo,
    HeatitDevice,
    OperatingMode,
    SensorData,
)

DISCOVERY_BASE = "https://tf.api.ouman-cloud.com"


class HeatitClient:
    """Client for the Heatit WiFi thermostat cloud API."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ):
        self._auth = CognitoAuth(username, password)
        self._session = session
        self._owns_session = session is None

        # GraphQL endpoints (discovered dynamically)
        self._device_endpoint: str | None = None
        self._data_endpoint: str | None = None
        self._events_endpoint: str | None = None
        self._users_endpoint: str | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _discover_endpoints(self) -> None:
        """Discover GraphQL endpoint URLs from the Ouman cloud."""
        session = self._get_session()
        timeout = aiohttp.ClientTimeout(total=10)

        try:
            for service, attr in [
                ("device", "_device_endpoint"),
                ("data", "_data_endpoint"),
                ("events", "_events_endpoint"),
                ("users", "_users_endpoint"),
            ]:
                async with session.get(
                    f"{DISCOVERY_BASE}/{service}/endpoint", timeout=timeout
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        setattr(self, attr, data.get("endpoint"))
        except aiohttp.ClientError as err:
            raise HeatitConnectionError(
                f"Failed to discover endpoints: {err}"
            ) from err

    async def _ensure_endpoints(self) -> None:
        if not self._device_endpoint:
            await self._discover_endpoints()

    async def _graphql(
        self, endpoint: str, operation: str, query: str, variables: dict | None = None
    ) -> dict:
        """Execute a GraphQL request."""
        session = self._get_session()
        token = await self._auth.authenticate()

        payload = {
            "operationName": operation,
            "query": query,
            "variables": variables or {},
        }

        try:
            async with session.post(
                endpoint,
                json=payload,
                headers={
                    "Authorization": token,
                    "Content-Type": "application/json",
                    "User-Agent": "Heatit/48 CFNetwork/3860.500.112 Darwin/25.4.0",
                    "x-amz-user-agent": "aws-amplify/2.0.5 react-native",
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise HeatitResponseError(
                        f"GraphQL request failed: {resp.status} {data}"
                    )
                if "errors" in data:
                    raise HeatitResponseError(
                        f"GraphQL errors: {data['errors']}"
                    )
                return data.get("data", {})
        except aiohttp.ClientError as err:
            raise HeatitConnectionError(f"Connection error: {err}") from err

    async def async_login(self) -> str:
        """Authenticate and return the user's email."""
        await self._ensure_endpoints()
        token = await self._auth.authenticate()

        data = await self._graphql(
            self._users_endpoint,
            "Query",
            """query Query {
  getCurrentUserDetails {
    email
    organizationId
    admin
  }
}""",
        )
        return data.get("getCurrentUserDetails", {}).get("email", "")

    async def async_get_devices(self) -> list[DeviceInfo]:
        """Get all devices from the device tree."""
        await self._ensure_endpoints()

        data = await self._graphql(
            self._device_endpoint,
            "Query",
            "query Query {\n  getDeviceTree\n}\n",
        )

        tree_str = data.get("getDeviceTree", "[]")
        tree = json.loads(tree_str)
        devices = []
        self._parse_device_tree(tree, devices)
        return devices

    def _parse_device_tree(
        self, nodes: list, devices: list[DeviceInfo], zone_name: str = ""
    ) -> None:
        """Recursively parse the device tree."""
        for node in nodes:
            node_type = node.get("t")
            if node_type == 0:  # Device
                info = DeviceInfo.from_tree_node(node, zone_name)
                devices.append(info)
            else:
                # Zone or org — recurse into children
                name = zone_name
                state = node.get("i", {}).get("state", {})
                if state.get("type") == "zone":
                    name = state.get("displayName", zone_name)
                self._parse_device_tree(node.get("c", []), devices, name)

    async def async_get_device_config(self, device_id: str) -> DeviceConfig:
        """Get device configuration (shadow state)."""
        await self._ensure_endpoints()

        data = await self._graphql(
            self._device_endpoint,
            "Query",
            """query Query($deviceId: ID!) {
  getDeviceState(deviceId: $deviceId) {
    desired
    reported
    metadata
    timestamp
    version
  }
}""",
            {"deviceId": device_id},
        )
        return DeviceConfig.from_state_response(data["getDeviceState"])

    async def async_get_sensor_data(self, device_id: str) -> SensorData:
        """Get live sensor readings."""
        await self._ensure_endpoints()

        data = await self._graphql(
            self._data_endpoint,
            "Query",
            """query Query($deviceId: String!) {
  getLatestData(deviceId: $deviceId) {
    deviceId
    timestamp
    sessionId
    type
    data
  }
}""",
            {"deviceId": device_id},
        )
        return SensorData.from_data_response(data["getLatestData"])

    async def async_get_device(self, device_id: str) -> HeatitDevice:
        """Get full device state (info + config + sensors)."""
        devices = await self.async_get_devices()
        info = next((d for d in devices if d.device_id == device_id), None)
        if not info:
            raise HeatitResponseError(f"Device {device_id} not found")

        config = await self.async_get_device_config(device_id)
        sensors = await self.async_get_sensor_data(device_id)
        return HeatitDevice(info=info, config=config, sensors=sensors)

    async def async_set_state(self, device_id: str, **kwargs) -> bool:
        """Set device state parameters via requestStateChange mutation.

        Args:
            device_id: The device UUID.
            **kwargs: State parameters, e.g. opMode=1, setPoint=230.
                      Temperature values should be in raw format (°C × 10).
        """
        await self._ensure_endpoints()

        state_json = json.dumps(kwargs)
        data = await self._graphql(
            self._device_endpoint,
            "Mutation",
            """mutation Mutation($deviceId: ID!, $state: AWSJSON!, $getFullState: Boolean) {
  requestStateChange(deviceId: $deviceId, state: $state, getFullState: $getFullState)
}""",
            {
                "deviceId": device_id,
                "state": state_json,
                "getFullState": False,
            },
        )
        return "requestStateChange" in data

    async def async_set_temperature(self, device_id: str, temp: float) -> bool:
        """Set target temperature in °C."""
        raw = int(round(temp * 10))
        return await self.async_set_state(device_id, setPoint=raw)

    async def async_set_mode(self, device_id: str, mode: OperatingMode) -> bool:
        """Set operating mode."""
        return await self.async_set_state(device_id, opMode=int(mode))

    async def async_ping(self, device_id: str) -> bool:
        """Send a ping/keepalive to the device."""
        import time

        ts = int(time.time() * 1000)
        return await self.async_set_state(device_id, cmd=f"ping({ts})")

    async def async_close(self) -> None:
        """Close the client and release resources."""
        await self._auth.close()
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> HeatitClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.async_close()
