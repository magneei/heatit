"""Config flow for the Heatit WiFi integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL

from .heatit_api import HeatitAuthError, HeatitClient, HeatitConnectionError

from .const import CONF_DEVICE_ID, CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HeatitConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Heatit WiFi."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._devices: list = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            try:
                async with HeatitClient(self._username, self._password) as client:
                    self._devices = await client.async_get_devices()
            except HeatitAuthError:
                errors["base"] = "auth_failed"
            except HeatitConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                if not self._devices:
                    errors["base"] = "no_devices"
                elif len(self._devices) == 1:
                    return await self._create_entry(self._devices[0])
                else:
                    return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device selection when multiple devices exist."""
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            device = next(d for d in self._devices if d.device_id == device_id)
            return await self._create_entry(device)

        device_options = {
            d.device_id: f"{d.zone_name} - {d.device_type}" if d.zone_name else d.device_type
            for d in self._devices
        }

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_ID): vol.In(device_options)}
            ),
        )

    async def _create_entry(self, device) -> ConfigFlowResult:
        """Create the config entry for a device."""
        await self.async_set_unique_id(device.mac_addr)
        self._abort_if_unique_id_configured()

        title = device.zone_name or device.device_type
        return self.async_create_entry(
            title=title,
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_DEVICE_ID: device.device_id,
            },
        )
