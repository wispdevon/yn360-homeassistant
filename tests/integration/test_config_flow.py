from unittest.mock import patch

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from yn360.const import SERVICE_UUID

from custom_components.yongnuo_yn360.const import (
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_YN360,
    DEVICE_TYPE_YN360_MINI,
    DOMAIN,
    device_type_from_name,
)

ADDRESS = "AA:BB:CC:DD:EE:FF"


def test_mini_device_names_are_classified_case_insensitively():
    assert device_type_from_name("YONGNUO LED") == DEVICE_TYPE_YN360_MINI
    assert device_type_from_name("YN360MiNi") == DEVICE_TYPE_YN360_MINI
    assert device_type_from_name("YN360 Mini") == DEVICE_TYPE_YN360_MINI


def _service_info(
    name: str = "YN360III_Pro", service_uuids: list[str] | None = None
) -> BluetoothServiceInfoBleak:
    """Build a BluetoothServiceInfoBleak directly.

    The HA test helpers ``generate_ble_device``/``generate_advertisement_data``
    are not exported by the installed pytest-homeassistant-custom-component, and
    ``from_advertisement`` is broken for the Bleak subclass in this version, so
    construct the object directly with all required fields.
    """
    uuids = [SERVICE_UUID] if service_uuids is None else service_uuids
    device = BLEDevice(ADDRESS, name, {})
    adv = AdvertisementData(
        local_name=name,
        manufacturer_data={},
        service_data={},
        service_uuids=uuids,
        tx_power=-127,
        rssi=-60,
        platform_data=(),
    )
    return BluetoothServiceInfoBleak(
        name, ADDRESS, -60, {}, {}, uuids, "local", device, adv, True, 0.0, -127
    )


async def test_bluetooth_discovery_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_service_info()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch(
        "custom_components.yongnuo_yn360.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "YN360III_Pro"
    assert result2["result"].unique_id == ADDRESS
    assert result2["data"] == {CONF_DEVICE_TYPE: DEVICE_TYPE_YN360}


async def test_bluetooth_discovery_accepts_mini_name_without_service_uuid(hass):
    """The Mini can be found by its generic advertised local name."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=_service_info(name="YONGNUO LED", service_uuids=[]),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch(
        "custom_components.yongnuo_yn360.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "YONGNUO LED"
    assert result2["data"] == {CONF_DEVICE_TYPE: DEVICE_TYPE_YN360_MINI}


async def test_manual_discovery_stores_mini_profile(hass):
    info = _service_info(name="YONGNUO LED", service_uuids=[])
    with patch(
        "custom_components.yongnuo_yn360.config_flow.async_discovered_service_info",
        return_value=[info],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.yongnuo_yn360.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"address": ADDRESS}
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {CONF_DEVICE_TYPE: DEVICE_TYPE_YN360_MINI}


async def test_bluetooth_discovery_rejects_non_yn360(hass):
    info = _service_info(name="RandomThing", service_uuids=[])
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=info
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"
