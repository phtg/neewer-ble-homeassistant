# Contributing

Thanks for helping make Neewer BLE Lights work with more hardware.

## Reporting a problem or testing a beta

Use the repository's issue forms for a bug report or device-support result. Include:

- The exact light model
- The complete Bluetooth advertised name
- The integration and Home Assistant versions
- Whether you use a local Bluetooth adapter or ESPHome Bluetooth proxy
- Which controls work: power, brightness, color temperature, and RGB color
- Debug logs with Bluetooth addresses and other private data removed

Hardware confirmation is especially valuable because maintainers do not have every supported Neewer light.

## Making a change

1. Fork the repository and create a focused branch.
2. Keep protocol and model changes covered by unit tests where possible.
3. Run the local checks:

   ```bash
   python -m json.tool hacs.json >/dev/null
   python -m json.tool custom_components/neewer_ble/manifest.json >/dev/null
   python -m json.tool custom_components/neewer_ble/strings.json >/dev/null
   python -m json.tool custom_components/neewer_ble/translations/en.json >/dev/null
   python -m compileall -q custom_components tests
   python -m unittest discover -s tests -v
   ```

4. Open a pull request and state whether the change was tested on physical hardware.

For a new device profile, use the exact Bluetooth advertised-name fragment and document its RGB support, color-temperature range, and protocol variant. A profile based only on another implementation or manufacturer documentation must be marked untested until a device owner confirms it.

## Attribution

If your change builds on another project, issue, or pull request, link it in the pull request description so the original contributor can be credited in the release notes.
