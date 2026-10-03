"""Diagnostic sensors for Yongnuo YN360."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, device_profile


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the YN360 diagnostic sensors from a config entry."""
    async_add_entities([YN360RSSISensor(entry)])


class YN360RSSISensor(SensorEntity):
    """Signal strength of the light's last received BLE advertisement."""

    _attr_has_entity_name = True
    _attr_translation_key = "signal_strength"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._address = entry.unique_id
        profile = device_profile(entry.data, entry.title)
        self._attr_unique_id = f"{entry.unique_id}_rssi"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            connections={("bluetooth", entry.unique_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=profile.model,
        )

    @property
    def available(self) -> bool:
        """Available only while the device is being seen by the BLE stack."""
        return bluetooth.async_address_present(
            self.hass, self._address, connectable=False
        )

    @property
    def native_value(self) -> int | None:
        """Return the RSSI from the most recent advertisement, if any."""
        info = bluetooth.async_last_service_info(
            self.hass, self._address, connectable=False
        )
        return info.rssi if info else None
