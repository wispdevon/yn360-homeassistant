"""YN360 Mini-specific BLE commands."""

from __future__ import annotations

from yn360 import YN360Light

MINI_RGB_HEADER = 0xAE
MINI_RGB_COMMAND = 0x05
MINI_RGB_PAYLOAD_LENGTH = 0x08
MINI_RGB_CHANNEL = 0x01
MINI_RGB_MAX = 99
MINI_RGB_POWER_ON = 0x01


def build_mini_rgb_command(
    r: int, g: int, b: int, brightness: float = 1.0
) -> bytes:
    """Build the Mini's 8-byte RGB command frame."""
    brightness = max(0.0, min(1.0, brightness))
    channels = tuple(
        round(max(0, min(255, value)) * brightness * MINI_RGB_MAX / 255)
        for value in (r, g, b)
    )
    return bytes(
        [
            MINI_RGB_HEADER,
            MINI_RGB_COMMAND,
            MINI_RGB_PAYLOAD_LENGTH,
            MINI_RGB_CHANNEL,
            *channels,
            MINI_RGB_POWER_ON,
        ]
    )


class YN360MiniLight(YN360Light):
    """YN360Light variant using the Mini's newer RGB command."""

    async def set_rgb(
        self, r: int, g: int, b: int, brightness: float = 1.0
    ) -> None:
        await self._write(build_mini_rgb_command(r, g, b, brightness))
