"""Constants for the Yongnuo YN360 integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

DOMAIN = "yongnuo_yn360"

LOGGER = logging.getLogger(__package__)

MANUFACTURER = "Yongnuo"

CONF_DEVICE_TYPE = "device_type"

DEVICE_TYPE_YN360 = "yn360"
DEVICE_TYPE_YN360_MINI = "yn360_mini"

# The Mini advertises this generic name rather than a YN360-prefixed name.
MINI_DEVICE_NAME_PREFIX = "YONGNUO LED"
MINI_MODEL_NAME_PREFIX = "YN360MINI"

# yn360-ble converts this logical Kelvin range into the protocol's warm/cool
# channel values. Mini temperatures are mapped onto it before calling the
# library because the Mini's physical range is wider.
PROTOCOL_MIN_KELVIN = 3200
PROTOCOL_MAX_KELVIN = 5500

# Bi-colour range of the YN360 III Pro. The official spec is 3200–5600 K; the
# defaults below are used unless overridden in the options flow.
DEFAULT_MIN_KELVIN = 3200
DEFAULT_MAX_KELVIN = 5600
MINI_MIN_KELVIN = 2700
MINI_MAX_KELVIN = 7800
MINI_MAX_RGB_CHANNEL = 99

# Options-flow keys.
CONF_PERSISTENT_CONNECTION = "persistent_connection"
CONF_MIN_KELVIN = "min_kelvin"
CONF_MAX_KELVIN = "max_kelvin"

DEFAULT_PERSISTENT_CONNECTION = False

# Connection retry policy. Each BLE command opens a short-lived connection
# (unless persistent), which can fail transiently when the light is busy or the
# proxy link is congested, so commands are retried with a linear backoff.
CONNECT_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = 0.5

# Software transition: the YN360 has no native fade, so a requested transition is
# emulated by stepping the brightness over the duration while holding a single
# connection. Steps are capped to keep the BLE traffic sane.
TRANSITION_STEP_SECONDS = 0.2
TRANSITION_MAX_STEPS = 30


@dataclass(frozen=True)
class DeviceProfile:
    """Model-specific behavior exposed by the integration."""

    device_type: str
    model: str
    min_kelvin: int
    max_kelvin: int


YN360_PROFILE = DeviceProfile(
    DEVICE_TYPE_YN360, "YN360 III Pro", DEFAULT_MIN_KELVIN, DEFAULT_MAX_KELVIN
)
YN360_MINI_PROFILE = DeviceProfile(
    DEVICE_TYPE_YN360_MINI, "YN360 Mini", MINI_MIN_KELVIN, MINI_MAX_KELVIN
)


def device_type_from_name(name: str | None) -> str:
    """Infer a device type from its advertised name."""
    normalized_name = (name or "").upper().replace(" ", "")
    mini_prefixes = (
        MINI_DEVICE_NAME_PREFIX.replace(" ", ""),
        MINI_MODEL_NAME_PREFIX,
    )
    if normalized_name.startswith(mini_prefixes):
        return DEVICE_TYPE_YN360_MINI
    return DEVICE_TYPE_YN360


def device_profile(data: Mapping[str, Any], title: str) -> DeviceProfile:
    """Return the profile for a config entry, including legacy entries."""
    device_type = data.get(CONF_DEVICE_TYPE, device_type_from_name(title))
    if (
        device_type == DEVICE_TYPE_YN360_MINI
        or device_type_from_name(title) == DEVICE_TYPE_YN360_MINI
    ):
        return YN360_MINI_PROFILE
    return YN360_PROFILE


def mini_protocol_kelvin(kelvin: int) -> int:
    """Map a physical Mini temperature onto yn360-ble's logical range."""
    clamped = max(MINI_MIN_KELVIN, min(MINI_MAX_KELVIN, kelvin))
    ratio = (clamped - MINI_MIN_KELVIN) / (MINI_MAX_KELVIN - MINI_MIN_KELVIN)
    return round(
        PROTOCOL_MIN_KELVIN
        + ratio * (PROTOCOL_MAX_KELVIN - PROTOCOL_MIN_KELVIN)
    )


def mini_protocol_rgb(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Scale Home Assistant RGB bytes to the Mini's 0-99 channel range."""
    return tuple(round(channel * MINI_MAX_RGB_CHANNEL / 255) for channel in rgb)
