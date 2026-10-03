from unittest.mock import AsyncMock

from custom_components.yongnuo_yn360.mini import (
    YN360MiniLight,
    build_mini_rgb_command,
)


def test_build_mini_rgb_command_colors():
    assert build_mini_rgb_command(255, 0, 0, 0.2) == bytes.fromhex(
        "AE 05 08 01 14 00 00 01"
    )
    assert build_mini_rgb_command(0, 0, 255, 80 / 99) == bytes.fromhex(
        "AE 05 08 01 00 00 50 01"
    )
    assert build_mini_rgb_command(255, 255, 0, 50 / 99) == bytes.fromhex(
        "AE 05 08 01 32 32 00 01"
    )


async def test_mini_light_writes_new_rgb_frame():
    light = object.__new__(YN360MiniLight)
    light._write = AsyncMock()

    await light.set_rgb(255, 0, 0, brightness=0.2)

    light._write.assert_awaited_once_with(bytes.fromhex("AE 05 08 01 14 00 00 01"))
