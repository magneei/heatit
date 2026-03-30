"""DataUpdateCoordinator for the Heatit WiFi integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from heatit_api import (
    HeatitAuthError,
    HeatitClient,
    HeatitConnectionError,
    HeatitDevice,
)

from .const import CONF_DEVICE_ID, CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HeatitDataUpdateCoordinator(DataUpdateCoordinator[HeatitDevice]):
    """Coordinator to poll Heatit device state."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.client = HeatitClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        self.device_id: str = entry.data[CONF_DEVICE_ID]

    async def _async_update_data(self) -> HeatitDevice:
        try:
            return await self.client.async_get_device(self.device_id)
        except HeatitAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Authentication failed: {err}"
            ) from err
        except HeatitConnectionError as err:
            raise UpdateFailed(
                f"Error communicating with Heatit cloud: {err}"
            ) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err
