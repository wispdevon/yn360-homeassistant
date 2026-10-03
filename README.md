<p align="center">
  <img src="assets/yongnuo-logo.png" alt="Yongnuo" width="420">
</p>

# Yongnuo YN360 for Home Assistant

[![Tests](https://github.com/hudsonbrendon/yn360-homeassistant/actions/workflows/test.yml/badge.svg)](https://github.com/hudsonbrendon/yn360-homeassistant/actions/workflows/test.yml)
[![Validate](https://github.com/hudsonbrendon/yn360-homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/yn360-homeassistant/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/yn360-homeassistant)](https://github.com/hudsonbrendon/yn360-homeassistant/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Auto-discovers **Yongnuo YN360, YN360 III Pro, and YN360 Mini** LED lights over
Bluetooth and exposes them as a Home Assistant `light` — on/off, brightness,
RGB colour, and white colour temperature.

The Bluetooth protocol and device control live in a separate Python library,
[**`yn360-ble`**](https://github.com/hudsonbrendon/yn360-ble)
([PyPI](https://pypi.org/project/yn360-ble/)), which this integration pulls in
automatically via `manifest.json` `requirements`.

## Features

- 🔍 **Automatic discovery** — power the light near Home Assistant and it shows up
  as a discovered device (no MAC address or YAML required).
- 💡 **On / off**
- 🔆 **Brightness** (0–100%)
- 🎨 **RGB colour**
- 🌡️ **White colour temperature** — 2700–7800 K on the YN360 Mini and
  3200–5600 K on other supported YN360 models (customisable in the options).
- 🌗 **Transitions** — software brightness fade via the `transition` parameter.
- ♻️ **State restore** — last on/off, brightness and colour survive a restart
  (the light has no feedback, so it's an `assumed_state` entity).
- 📶 **Availability tracking** — goes unavailable when out of range, recovers
  automatically, and exposes an optional diagnostic **signal-strength (RSSI)**
  sensor.
- 🔁 **Resilient commands** — Bluetooth commands are retried with a backoff on
  transient errors.
- ⚙️ **Options** — persistent vs per-command Bluetooth connection, and a custom
  colour-temperature range.
- 📡 **Works through ESPHome Bluetooth proxies** — it uses Home Assistant's shared
  Bluetooth stack, so the light doesn't need to be near the HA host, only near a
  proxy.

## Requirements

- Home Assistant **2024.12** or newer.
- A Bluetooth adapter on the Home Assistant host **or** an
  [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)
  within range of the light.
- A Yongnuo YN360 Mini, YN360 III Pro, or another YN360 model using the same
  BLE protocol.

## Installation

### HACS (recommended)

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Add the repository URL `https://github.com/hudsonbrendon/yn360-homeassistant`
   and choose the **Integration** category.
3. Search for **Yongnuo YN360** in HACS, install it, and **restart Home Assistant**.

### Manual

1. Copy `custom_components/yongnuo_yn360/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Power on the light within range of Home Assistant (or a Bluetooth proxy).
2. Home Assistant discovers it automatically — go to
   **Settings → Devices & Services** and you'll see a **Yongnuo YN360**
   *Discovered* card. Click **Configure → Submit**.
3. If it isn't auto-discovered, add it manually: **Settings → Devices & Services
   → Add Integration → Yongnuo YN360**, then pick the device from the list.

There is nothing else to configure — the light entity appears immediately.

## Usage

The integration creates a single `light` entity per device. From the entity (UI,
automations, scripts, or the `light.turn_on` / `light.turn_off` services) you can:

| Capability | Detail |
|---|---|
| Power | On / off |
| Brightness | `brightness` / `brightness_pct` |
| Colour | `rgb_color` |
| Colour temperature | `color_temp_kelvin` (3200–5600 K, configurable) |
| Transition | `transition` (seconds, software fade) |

## Options

After adding the device, open **Settings → Devices & Services → Yongnuo YN360 →
Configure**:

| Option | Default | What it does |
|---|---|---|
| Keep the Bluetooth connection open | Off | When on, holds a persistent connection for lower latency. Trade-off: it occupies a Bluetooth slot and blocks the official Yongnuo app. Leave off to connect only while sending a command. |
| Minimum / maximum colour temperature | Model-specific | Override the white range exposed to Home Assistant. Defaults are 2700 / 7800 K for the YN360 Mini and 3200 / 5600 K for other supported models. |

Example automation:

```yaml
service: light.turn_on
target:
  entity_id: light.yn360iii_pro
data:
  rgb_color: [255, 153, 0]
  brightness_pct: 80
```

## How it works

This repository ships **only** the Home Assistant integration. All Bluetooth
work — connecting, building the command frames, RGB/white conversions — lives in
the [`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) Python library and
is pulled in as a dependency. The YN360 Mini uses the same service UUID, write
characteristic, and 6-byte command frames as the other supported lights; the
integration maps its wider 2700–7800 K range onto those warm/cool channel values.
Commands use acknowledged writes because supported hardware may ignore
write-without-response.

YN360 Mini discovery and protocol compatibility are based on the working
[`YN360_Mac`](https://github.com/pinchies/YN360_Mac) implementation, where the
Mini advertises as `YONGNUO LED`.

## Limitations

- The light has **no state feedback** over Bluetooth, so the entity is
  `assumed_state` — Home Assistant shows the last commanded state, which may drift
  if the light is changed by its physical buttons or another app.
- Bluetooth LE allows **one client at a time** — close the official Yongnuo app
  while Home Assistant is controlling the light.
- RGB and white are mutually exclusive modes; setting one switches the active mode.

## Roadmap

The device also has hardware features not yet exposed here because they require
reverse-engineering the BLE command frames in the
[`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) library first:

- **Special effects / scenes** (lightning, sunrise, candle, police, TV,
  fireworks, strobe…) — would map to Home Assistant's light `effect_list`.
- **Green–magenta (GM) tint** adjustment for the white modes.

These are blocked on the protocol library, not the integration; contributions of
sniffed command frames are welcome there.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Protocol/decoding changes belong in the
[`yn360-ble`](https://github.com/hudsonbrendon/yn360-ble) library, not here.

## License

[MIT](LICENSE) © Hudson Brendon
