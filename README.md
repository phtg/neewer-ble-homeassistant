# Neewer BLE Lights for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://www.hacs.xyz/)
[![HACS validation](https://github.com/phtg/neewer-ble-homeassistant/actions/workflows/hacs.yml/badge.svg)](https://github.com/phtg/neewer-ble-homeassistant/actions/workflows/hacs.yml)
[![Hassfest validation](https://github.com/phtg/neewer-ble-homeassistant/actions/workflows/hassfest.yml/badge.svg)](https://github.com/phtg/neewer-ble-homeassistant/actions/workflows/hassfest.yml)
[![Tests](https://github.com/phtg/neewer-ble-homeassistant/actions/workflows/tests.yml/badge.svg)](https://github.com/phtg/neewer-ble-homeassistant/actions/workflows/tests.yml)

A Home Assistant custom integration for controlling Neewer LED lights via Bluetooth Low Energy (BLE).

## Supported Devices

This integration supports Neewer lights that use Bluetooth for control, including:

### Tested

- **GL1 Pro** - Key Light

### Should Work (Untested)

- MS60C - 65W RGB COB Light
- RGB660 / RGB660 PRO - Panel Lights
- RGB480 / RGB530 - Panel Lights
- SL-80 - Bi-Color Panel
- SNL-660 - Bi-Color Panel
- GL1 - Key Light
- CB100C / CB300B - COB Lights
- RGB1 - Light Wand
- TL60 RGB - Tube Light

### Beta - Community Testing Needed

- **MS150B** - `MS150B-*` Bluetooth name variant
- **PL60C** - RGB Panel Light
- **AP150C** - RGB Panel Light
- **RGB168** - RGB Panel Light

These profiles are based on published protocol implementations and manufacturer specifications, but have not yet been tested with physical hardware in this integration.

## Features

- **Brightness control** (0-100%)
- **Color temperature control** (varies by model, typically 2700K-6500K)
- **RGB color control** (for supported models)
- **Auto-discovery** via Home Assistant's Bluetooth integration
- **Manual device entry** for devices not auto-discovered
- **Optional persistent Bluetooth connection** for faster, more reliable commands

## Requirements

- Home Assistant 2024.1.0 or newer
- Bluetooth adapter on your Home Assistant host
- OR an ESPHome Bluetooth Proxy

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL: `https://github.com/phtg/neewer-ble-homeassistant`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Neewer BLE" and install it
8. Restart Home Assistant

Beta releases are hidden by default. To help test a prerelease, open the Neewer BLE Lights repository in HACS, enable **Show beta versions**, choose the beta version, download it, and restart Home Assistant.

### Manual Installation

1. Download the `custom_components/neewer_ble` folder from this repository
2. Copy it to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Automatic Discovery

If your Neewer light is powered on and in range, Home Assistant should automatically discover it. You'll see a notification to configure the new device.

### Manual Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Neewer BLE"
4. Select your light from the discovered devices, or enter the Bluetooth address manually

### Options

Open **Settings** → **Devices & Services** → **Neewer BLE Lights**, select **Configure**, and adjust:

- **Default brightness** used when turning on without an explicit brightness
- **Default color temperature** used when turning on without an explicit color temperature
- **Keep Bluetooth connection active** for faster commands and improved reliability

Keeping the connection active prevents the Neewer app or another controller from connecting until Home Assistant releases it.

## Usage

Once configured, your Neewer light will appear as a light entity in Home Assistant. You can:

- Turn it on/off
- Adjust brightness
- Change color temperature (in Kelvin)
- Set RGB colors (if supported by your model)

### Example Automations

```yaml
# Turn on light when camera is active
automation:
  - alias: "Studio Light On When Recording"
    trigger:
      - platform: state
        entity_id: binary_sensor.camera_active
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.neewer_ms150b
        data:
          brightness_pct: 80
          color_temp_kelvin: 5600
```

```yaml
# Dim lights for video call
script:
  video_call_lighting:
    sequence:
      - service: light.turn_on
        target:
          entity_id: light.neewer_ms150b
        data:
          brightness_pct: 60
          color_temp_kelvin: 4500
```

## Troubleshooting

### Light Not Discovered

1. Make sure the light is powered on
2. Ensure Bluetooth is enabled on your Home Assistant host
3. Try moving the light closer to your Bluetooth adapter
4. Check that no other device (like the Neewer app) is connected to the light

### Connection Issues

Bluetooth connections can be finicky. Try:

- Restarting the light
- Restarting Home Assistant
- Using an ESPHome Bluetooth Proxy for better range/reliability

### Light Not Responding

Some Neewer lights use different BLE protocols. If your light isn't responding:

1. Disconnect the Neewer mobile or desktop app from the light
2. Enable debug logging and retry the command
3. [Open a bug report](https://github.com/phtg/neewer-ble-homeassistant/issues/new?template=bug_report.yml) with the exact model, Bluetooth advertised name, and sanitized logs

### Debug Logging

Add this to `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  logs:
    custom_components.neewer_ble: debug
```

Reproduce the problem, then open **Settings** → **System** → **Logs**. Remove Bluetooth addresses or other private data before attaching logs to an issue.

## Known Limitations

- The integration controls the light over Bluetooth only; it does not use the light's Wi-Fi connection.
- Changes made from the Neewer app or another computer are not reflected in Home Assistant. Brightness and color state in Home Assistant are optimistic and represent the most recent command Home Assistant sent.
- A Bluetooth light generally accepts one active controller. Disconnect the Neewer app before using Home Assistant, especially when **Keep Bluetooth connection active** is enabled.
- Devices in the beta list need confirmation from owners with physical hardware.

## Removal

1. Open **Settings** → **Devices & Services** → **Neewer BLE Lights** and delete each configured light.
2. In HACS, open **Neewer BLE Lights**, choose **Remove**, and restart Home Assistant.
3. For a manual installation, remove `custom_components/neewer_ble` from the Home Assistant configuration directory and restart.

## Contributing

Contributions and hardware test results are welcome. Use the [device support and beta feedback form](https://github.com/phtg/neewer-ble-homeassistant/issues/new?template=device_support.yml) for a light that is missing or needs confirmation. See [CONTRIBUTING.md](CONTRIBUTING.md) before submitting code.

## Protocol Information

This integration is based on the reverse-engineered Neewer BLE protocol from:

- [NeewerLite](https://github.com/keefo/NeewerLite) (macOS)
- [NeewerLite-Python](https://github.com/taburineagle/NeewerLite-Python) (Cross-platform)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by Neewer.
