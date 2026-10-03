from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yongnuo_yn360.const import (
    CONF_DEVICE_TYPE,
    CONF_MAX_KELVIN,
    CONF_MIN_KELVIN,
    CONF_PERSISTENT_CONNECTION,
    DEVICE_TYPE_YN360_MINI,
    DOMAIN,
)

ADDRESS = "AA:BB:CC:DD:EE:FF"


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS, data={}, title="YN360III_Pro"
    )


async def test_options_flow_saves_values(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PERSISTENT_CONNECTION: True,
            CONF_MIN_KELVIN: 2700,
            CONF_MAX_KELVIN: 6500,
        },
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_PERSISTENT_CONNECTION] is True
    assert entry.options[CONF_MIN_KELVIN] == 2700
    assert entry.options[CONF_MAX_KELVIN] == 6500


async def test_options_flow_rejects_inverted_range(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PERSISTENT_CONNECTION: False,
            CONF_MIN_KELVIN: 6000,
            CONF_MAX_KELVIN: 3000,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_kelvin_range"}


async def test_options_flow_uses_mini_kelvin_defaults(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        data={CONF_DEVICE_TYPE: DEVICE_TYPE_YN360_MINI},
        title="YONGNUO LED",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    defaults = result["data_schema"]({})
    assert defaults[CONF_MIN_KELVIN] == 2700
    assert defaults[CONF_MAX_KELVIN] == 7800
