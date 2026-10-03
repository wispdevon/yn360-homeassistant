import json
from pathlib import Path


def test_manifest_is_valid():
    path = Path("custom_components/yongnuo_yn360/manifest.json")
    data = json.loads(path.read_text())
    assert data["domain"] == "yongnuo_yn360"
    assert data["config_flow"] is True
    assert data["iot_class"] == "assumed_state"
    assert "bluetooth_adapters" in data["dependencies"]
    # The III Pro advertises the service UUID as well as the name (confirmed
    # against hardware, see yn360-ble HARDWARE.md), so discovery matches on
    # both -- a unit advertising an unexpected name is still found.
    assert data["bluetooth"] == [
        {"local_name": "YN360*"},
        {"local_name": "YONGNUO LED*"},
        {"service_uuid": "f000aa60-0451-4000-b000-000000000000"},
    ]
    assert data["version"] == "0.4.3"
    assert any(r.startswith("yn360-ble") for r in data["requirements"])
