# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.3] - 2026-10-04

### Fixed
- **YN360 Mini RGB mode switching** — use the Mini's newer 8-byte RGB frame.
  Live hardware testing confirmed red, blue, and mixed-channel yellow output;
  the legacy `0xA1` RGB frame used by other YN360 models is ignored by the Mini.

## [0.4.2] - 2026-10-04

### Fixed
- **YN360 Mini RGB control** — scale Home Assistant's 0–255 RGB channels to
  the Mini protocol's 0–99 range. Values above 99 were ignored by the light,
  while colour-temperature commands continued to work.

## [0.4.1] - 2026-10-03

### Added
- **Yongnuo YN360 Mini support** — discovery now recognizes the Mini's
  `YONGNUO LED` advertised name, and device metadata identifies it separately
  from the YN360 III Pro.
- **Full Mini colour-temperature range** — Home Assistant exposes 2700–7800 K
  and maps it onto the existing warm/cool BLE protocol.

### Changed
- New config entries persist their detected device profile. Existing entries
  remain compatible and infer the Mini profile from their saved title.
- The integration version is now 0.4.1.

## [0.3.0] - 2026-08-20

### Changed
- **Connections now go through `bleak-retry-connector`'s `establish_connection`.**
  Previously the integration only borrowed that library's exception list while
  opening connections itself. Going through `establish_connection` adds
  connection-slot management and GATT service caching, which matter most when
  the light is reached through an ESPHome Bluetooth proxy rather than a local
  adapter.
- **Discovery also matches the advertised service UUID**, not just the device
  name, so a unit advertising an unexpected name is still discovered. The
  YN360 III Pro was confirmed to advertise `f000aa60-…` in its advertisement
  packet.
- Requires `yn360-ble` 0.2.0.

### Notes
- The device was verified to emit **no** BLE notifications — not for app-sent
  commands, and not when its physical knobs are turned. There is no state
  feedback to read, so the light stays an `assumed_state` entity. It also has
  no battery GATT service, so a battery level sensor is not possible.

## [0.2.0] - 2026-05-28

### Added
- **Connection resilience** — each BLE command is now retried with a backoff on
  transient Bluetooth errors instead of failing on the first hiccup.
- **Availability tracking** — the light is marked unavailable when it stops
  advertising and recovers automatically when it is seen again.
- **State restore** — the last commanded on/off, brightness, colour and colour
  temperature survive a Home Assistant restart.
- **Transitions** — `light.turn_on` / `light.turn_off` honour `transition` via a
  software brightness fade.
- **Options flow** — choose a persistent vs per-command Bluetooth connection and
  customise the colour-temperature range.
- **Signal-strength sensor** — a diagnostic (disabled-by-default) RSSI sensor.
- **Diagnostics** — downloadable config-entry diagnostics.

### Changed
- Default white range widened to the device's full 3200–5600 K (was 3200–5500 K).

## [0.1.0] - 2026-05-25

### Added
- Initial release: Bluetooth auto-discovery + config flow and a `light` entity
  (on/off, brightness, RGB colour, and 3200–5500 K white colour temperature) for
  the Yongnuo YN360 / YN360 III Pro, backed by the
  [`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) library.
- GitHub Actions: `pytest` on every push/PR, plus `hassfest` and HACS validation.
- English, Portuguese (pt-BR, pt), and Spanish (es) translations.

[Unreleased]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.4.3...HEAD
[0.4.3]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.3.0...v0.4.1
[0.3.0]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/hudsonbrendon/yn360-homeassistant/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/hudsonbrendon/yn360-homeassistant/releases/tag/v0.1.0
