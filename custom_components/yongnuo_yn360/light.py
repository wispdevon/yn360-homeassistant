"""Light platform for Yongnuo YN360."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from bleak import BleakClient
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS, establish_connection
from homeassistant.components import bluetooth
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from yn360 import YN360Light

from .const import (
    CONF_MAX_KELVIN,
    CONF_MIN_KELVIN,
    CONF_PERSISTENT_CONNECTION,
    CONNECT_ATTEMPTS,
    DEFAULT_PERSISTENT_CONNECTION,
    DEVICE_TYPE_YN360_MINI,
    DOMAIN,
    LOGGER,
    MANUFACTURER,
    RETRY_BACKOFF_SECONDS,
    TRANSITION_MAX_STEPS,
    TRANSITION_STEP_SECONDS,
    device_profile,
    mini_protocol_kelvin,
)
from .mini import YN360MiniLight


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Yongnuo YN360 light from a config entry."""
    async_add_entities([YN360LightEntity(entry)])


class YN360LightEntity(LightEntity, RestoreEntity):
    """A Yongnuo YN360 RGB / bi-colour BLE light.

    The light has no state feedback over BLE, so it is an ``assumed_state``
    entity whose last commanded state is restored across restarts. Commands are
    sent over Home Assistant's shared Bluetooth stack (so they also work through
    ESPHome BT proxies) and retried with a backoff on transient failures. By
    default each command opens a short-lived connection; a persistent connection
    can be enabled in the options for lower latency.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}
    _attr_supported_features = LightEntityFeature.TRANSITION

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._address = entry.unique_id
        self._profile = device_profile(entry.data, entry.title)
        self._attr_unique_id = entry.unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            connections={("bluetooth", entry.unique_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=self._profile.model,
        )
        self._attr_min_color_temp_kelvin = entry.options.get(
            CONF_MIN_KELVIN, self._profile.min_kelvin
        )
        self._attr_max_color_temp_kelvin = entry.options.get(
            CONF_MAX_KELVIN, self._profile.max_kelvin
        )
        self._persistent = entry.options.get(
            CONF_PERSISTENT_CONNECTION, DEFAULT_PERSISTENT_CONNECTION
        )
        self._device: YN360Light | None = None
        self._lock = asyncio.Lock()
        self._attr_available = False
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_color_temp_kelvin = (
            self._attr_min_color_temp_kelvin + self._attr_max_color_temp_kelvin
        ) // 2
        self._attr_color_mode = ColorMode.RGB

    async def async_added_to_hass(self) -> None:
        """Restore the last commanded state and start tracking availability."""
        await super().async_added_to_hass()

        if (last := await self.async_get_last_state()) is not None:
            self._attr_is_on = last.state == "on"
            attrs = last.attributes
            if (brightness := attrs.get(ATTR_BRIGHTNESS)) is not None:
                self._attr_brightness = brightness
            if (rgb := attrs.get(ATTR_RGB_COLOR)) is not None:
                self._attr_rgb_color = tuple(rgb)
            if (kelvin := attrs.get(ATTR_COLOR_TEMP_KELVIN)) is not None:
                self._attr_color_temp_kelvin = kelvin
            if (mode := attrs.get("color_mode")) in (
                ColorMode.RGB,
                ColorMode.COLOR_TEMP,
            ):
                self._attr_color_mode = mode

        self._attr_available = bluetooth.async_address_present(
            self.hass, self._address, connectable=True
        )

        self.async_on_remove(
            bluetooth.async_register_callback(
                self.hass,
                self._async_on_advertisement,
                {"address": self._address, "connectable": True},
                bluetooth.BluetoothScanningMode.ACTIVE,
            )
        )
        self.async_on_remove(
            bluetooth.async_track_unavailable(
                self.hass,
                self._async_on_unavailable,
                self._address,
                connectable=True,
            )
        )

    async def async_will_remove_from_hass(self) -> None:
        """Drop any persistent connection when the entity goes away."""
        await self._async_close()

    @callback
    def _async_on_advertisement(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Mark the light available again when it is seen advertising."""
        if not self._attr_available:
            self._attr_available = True
            self.async_write_ha_state()

    @callback
    def _async_on_unavailable(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Mark the light unavailable when it stops advertising."""
        self._attr_available = False
        self.async_write_ha_state()

    def _make_device(self) -> YN360Light:
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )
        if ble_device is None:
            raise HomeAssistantError(f"YN360 {self._address} is not in range")

        def _connect() -> Awaitable[BleakClient]:
            # establish_connection manages the adapter's connection slots and
            # caches GATT services; both matter when the light is reached
            # through an ESPHome Bluetooth proxy rather than a local adapter.
            return establish_connection(
                BleakClient, ble_device, self._address, max_attempts=2
            )

        device_class = (
            YN360MiniLight
            if self._profile.device_type == DEVICE_TYPE_YN360_MINI
            else YN360Light
        )
        return device_class(ble_device, client_factory=_connect)

    async def _async_close(self) -> None:
        """Disconnect and forget any cached device."""
        if self._device is not None:
            try:
                await self._device.disconnect()
            except BLEAK_RETRY_EXCEPTIONS:  # pragma: no cover - best effort
                pass
            self._device = None

    async def _async_run(
        self, action: Callable[[YN360Light], Awaitable[None]]
    ) -> None:
        """Run ``action`` against the device, with retries and backoff.

        A fresh device/connection is built for each attempt so a half-open BLE
        link from a previous failure cannot wedge the entity. On success the
        connection is kept open only when persistent mode is enabled.
        """
        async with self._lock:
            last_exc: Exception | None = None
            for attempt in range(CONNECT_ATTEMPTS):
                device = self._device or self._make_device()
                try:
                    await action(device)
                except BLEAK_RETRY_EXCEPTIONS as err:
                    last_exc = err
                    LOGGER.debug(
                        "YN360 %s command attempt %s/%s failed: %s",
                        self._address,
                        attempt + 1,
                        CONNECT_ATTEMPTS,
                        err,
                    )
                    self._device = None
                    try:
                        await device.disconnect()
                    except BLEAK_RETRY_EXCEPTIONS:
                        pass
                    if attempt + 1 < CONNECT_ATTEMPTS:
                        await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                else:
                    if self._persistent:
                        self._device = device
                    else:
                        await device.disconnect()
                        self._device = None
                    return
            raise HomeAssistantError(
                f"YN360 {self._address} command failed after {CONNECT_ATTEMPTS} "
                f"attempts: {last_exc}"
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on, optionally setting colour, colour temperature, or brightness."""
        transition = kwargs.get(ATTR_TRANSITION)
        target_brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness or 255)

        kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN, self._attr_color_temp_kelvin)
        rgb = kwargs.get(ATTR_RGB_COLOR, self._attr_rgb_color)

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            mode = ColorMode.COLOR_TEMP
        elif ATTR_RGB_COLOR in kwargs:
            mode = ColorMode.RGB
        else:
            mode = self._attr_color_mode

        def _emit(device: YN360Light, brightness: int) -> Awaitable[None]:
            ratio = brightness / 255
            if mode == ColorMode.COLOR_TEMP:
                protocol_kelvin = (
                    mini_protocol_kelvin(kelvin)
                    if self._profile.device_type == DEVICE_TYPE_YN360_MINI
                    else kelvin
                )
                return device.set_white(protocol_kelvin, ratio)
            return device.set_rgb(*rgb, brightness=ratio)

        if transition and transition > 0:
            start = self._attr_brightness if self._attr_is_on else 0

            async def _faded(device: YN360Light) -> None:
                steps = max(
                    1,
                    min(
                        TRANSITION_MAX_STEPS,
                        int(transition / TRANSITION_STEP_SECONDS),
                    ),
                )
                for step in range(1, steps + 1):
                    level = round(start + (target_brightness - start) * step / steps)
                    await _emit(device, max(1, level))
                    if step < steps:
                        await asyncio.sleep(transition / steps)

            await self._async_run(_faded)
        else:
            await self._async_run(lambda device: _emit(device, target_brightness))

        self._attr_color_mode = mode
        if mode == ColorMode.COLOR_TEMP:
            self._attr_color_temp_kelvin = kelvin
        else:
            self._attr_rgb_color = rgb
        self._attr_brightness = target_brightness
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        transition = kwargs.get(ATTR_TRANSITION)

        if transition and transition > 0 and self._attr_is_on:
            start = self._attr_brightness or 255
            mode = self._attr_color_mode

            async def _faded(device: YN360Light) -> None:
                steps = max(
                    1,
                    min(
                        TRANSITION_MAX_STEPS,
                        int(transition / TRANSITION_STEP_SECONDS),
                    ),
                )
                for step in range(1, steps + 1):
                    level = round(start * (steps - step) / steps)
                    ratio = max(0, level) / 255
                    if level <= 0:
                        await device.turn_off()
                    elif mode == ColorMode.COLOR_TEMP:
                        kelvin = self._attr_color_temp_kelvin
                        if self._profile.device_type == DEVICE_TYPE_YN360_MINI:
                            kelvin = mini_protocol_kelvin(kelvin)
                        await device.set_white(kelvin, ratio)
                    else:
                        await device.set_rgb(*self._attr_rgb_color, brightness=ratio)
                    if step < steps:
                        await asyncio.sleep(transition / steps)

            await self._async_run(_faded)
        else:
            await self._async_run(lambda device: device.turn_off())

        self._attr_is_on = False
        self.async_write_ha_state()
