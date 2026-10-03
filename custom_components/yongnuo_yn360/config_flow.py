"""Config flow for Yongnuo YN360."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from yn360.const import DEVICE_NAME_PREFIX, SERVICE_UUID

from .const import (
    CONF_DEVICE_TYPE,
    CONF_MAX_KELVIN,
    CONF_MIN_KELVIN,
    CONF_PERSISTENT_CONNECTION,
    DEFAULT_PERSISTENT_CONNECTION,
    DOMAIN,
    MINI_DEVICE_NAME_PREFIX,
    device_profile,
    device_type_from_name,
)


def _supports(info: BluetoothServiceInfoBleak) -> bool:
    """Return True when a discovered BLE device looks like a Yongnuo YN360."""
    name = (info.name or "").upper()
    uuids = [u.lower() for u in info.service_uuids]
    prefixes = (DEVICE_NAME_PREFIX.upper(), MINI_DEVICE_NAME_PREFIX)
    return name.startswith(prefixes) or SERVICE_UUID in uuids


class YN360ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yongnuo YN360."""

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> YN360OptionsFlow:
        """Return the options flow handler."""
        return YN360OptionsFlow()

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a discovery via the bluetooth integration."""
        if not _supports(discovery_info):
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding a discovered device."""
        assert self._discovery is not None
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery.name,
                data={
                    CONF_DEVICE_TYPE: device_type_from_name(self._discovery.name)
                },
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovery.name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the manual/user step listing discovered devices."""
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            info = self._discovered[address]
            return self.async_create_entry(
                title=info.name,
                data={CONF_DEVICE_TYPE: device_type_from_name(info.name)},
            )

        current = self._async_current_ids()
        for info in async_discovered_service_info(self.hass):
            if info.address in current or info.address in self._discovered:
                continue
            if _supports(info):
                self._discovered[info.address] = info

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("address"): vol.In(
                        {a: i.name for a, i in self._discovered.items()}
                    )
                }
            ),
        )


class YN360OptionsFlow(OptionsFlow):
    """Handle YN360 options: connection behaviour and colour-temperature range."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        options = self.config_entry.options
        profile = device_profile(self.config_entry.data, self.config_entry.title)

        if user_input is not None:
            if user_input[CONF_MIN_KELVIN] >= user_input[CONF_MAX_KELVIN]:
                errors["base"] = "invalid_kelvin_range"
            else:
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PERSISTENT_CONNECTION,
                    default=options.get(
                        CONF_PERSISTENT_CONNECTION, DEFAULT_PERSISTENT_CONNECTION
                    ),
                ): bool,
                vol.Required(
                    CONF_MIN_KELVIN,
                    default=options.get(CONF_MIN_KELVIN, profile.min_kelvin),
                ): vol.All(vol.Coerce(int), vol.Range(min=1000, max=10000)),
                vol.Required(
                    CONF_MAX_KELVIN,
                    default=options.get(CONF_MAX_KELVIN, profile.max_kelvin),
                ): vol.All(vol.Coerce(int), vol.Range(min=1000, max=10000)),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
