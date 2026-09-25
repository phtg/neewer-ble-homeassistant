"""The Neewer BLE Lights integration."""

from __future__ import annotations

import logging

from bleak.backends.device import BLEDevice
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_DEFAULT_BRIGHTNESS,
    CONF_DEFAULT_COLOR_TEMP,
    CONF_KEEP_CONNECTED,
    DEFAULT_BRIGHTNESS,
    DEFAULT_COLOR_TEMP,
    DOMAIN,
)
from .neewer_device import NeewerLightDevice

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]

type NeewerBLEConfigEntry = ConfigEntry[NeewerLightDevice]


async def async_setup_entry(
    hass: HomeAssistant, entry: NeewerBLEConfigEntry
) -> bool:
    """Set up Neewer BLE Lights from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    name: str = entry.data.get("name", "Neewer Light")

    _LOGGER.info("Setting up Neewer BLE device: %s (%s)", name, address)

    def _ble_device_callback() -> BLEDevice | None:
        """Return the freshest BLE device from Home Assistant's shared scanner."""
        return async_ble_device_from_address(
            hass, address.upper(), connectable=True
        )

    ble_device = _ble_device_callback()

    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Bluetooth device {name} ({address}) is not currently available"
        )

    _LOGGER.info("Found BLE device: %s (%s)", ble_device.name, ble_device.address)

    # Get options with defaults
    default_brightness = entry.options.get(CONF_DEFAULT_BRIGHTNESS, DEFAULT_BRIGHTNESS)
    default_color_temp = entry.options.get(CONF_DEFAULT_COLOR_TEMP, DEFAULT_COLOR_TEMP)
    keep_connected = entry.options.get(CONF_KEEP_CONNECTED, False)

    # Create the device handler
    device = NeewerLightDevice(
        ble_device,
        default_brightness=default_brightness,
        default_color_temp=default_color_temp,
        keep_connected=keep_connected,
        ble_device_callback=_ble_device_callback,
    )
    _LOGGER.info(
        "Created device handler - Model: %s, RGB: %s, Infinity: %s, Default Bri: %d, Default CT: %dK, Keep Conn: %s",
        device.model_name,
        device.supports_rgb,
        device.uses_infinity_protocol,
        default_brightness,
        default_color_temp,
        keep_connected,
    )

    entry.runtime_data = device

    # Set up platforms
    _LOGGER.debug("Forwarding setup to platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("Setup complete for %s", name)
    return True


async def async_update_options(
    hass: HomeAssistant, entry: NeewerBLEConfigEntry
) -> None:
    """Handle options update."""
    device = entry.runtime_data

    default_brightness = entry.options.get(CONF_DEFAULT_BRIGHTNESS, DEFAULT_BRIGHTNESS)
    default_color_temp = entry.options.get(CONF_DEFAULT_COLOR_TEMP, DEFAULT_COLOR_TEMP)
    keep_connected = entry.options.get(CONF_KEEP_CONNECTED, False)

    device.set_defaults(default_brightness, default_color_temp, keep_connected)
    _LOGGER.info(
        "Updated defaults for %s - Brightness: %d, Color Temp: %dK, Keep Conn: %s",
        device.name,
        default_brightness,
        default_color_temp,
        keep_connected,
    )


async def async_unload_entry(
    hass: HomeAssistant, entry: NeewerBLEConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Neewer BLE device: %s", entry.data.get(CONF_ADDRESS))

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await entry.runtime_data.disconnect()

    return unload_ok


async def async_migrate_entry(
    hass: HomeAssistant, entry: NeewerBLEConfigEntry
) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    # No migrations needed yet
    return True
