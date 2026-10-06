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

### Checking automatic discovery

With the integration installed and Home Assistant restarted, check a powered, in-range light that has not previously been configured in Home Assistant. Disconnect the Neewer app from the light, then look for a discovered Neewer integration in **Settings → Devices & Services** before using **Add Integration** or entering a Bluetooth address. Finding or adding a light through manual setup does not confirm automatic discovery.

Record the automatic-discovery result, integration and Home Assistant versions, complete Bluetooth advertised name, and Bluetooth transport (local adapter, ESPHome proxy, both, or other/unknown) in the [device support and beta feedback form](https://github.com/phtg/neewer-ble-homeassistant/issues/new?template=device_support.yml). Keep discovery observations separate from control results, and put discovery failure observations in **Test details**.

If you did not check discovery before manual setup, choose **Not checked**. If the light is already configured, choose **Already configured so discovery was not checked**; keep working entries in place. Both options leave automatic discovery unverified, even if controls work.

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
