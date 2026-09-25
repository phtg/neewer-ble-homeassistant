"""Home Assistant lifecycle tests for Neewer BLE."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.neewer_ble import async_setup_entry
from custom_components.neewer_ble.const import DOMAIN


def _runtime_device() -> SimpleNamespace:
    """Create a complete device surface for platform setup."""
    return SimpleNamespace(
        address="AA:BB:CC:DD:EE:FF",
        name="NEEWER-GL1 PRO",
        model_name="GL1 Pro",
        supports_rgb=False,
        uses_infinity_protocol=False,
        color_temp_range=(2900, 7000),
        hue=0,
        saturation=100,
        brightness=100,
        color_temp_kelvin=3200,
        is_on=False,
        turn_on=AsyncMock(return_value=True),
        turn_off=AsyncMock(return_value=True),
        set_rgb=AsyncMock(return_value=True),
        disconnect=AsyncMock(),
        set_defaults=Mock(),
    )


def _config_entry() -> MockConfigEntry:
    """Create a Neewer config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="NEEWER-GL1 PRO",
        unique_id="AA:BB:CC:DD:EE:FF",
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "NEEWER-GL1 PRO",
        },
    )


async def _setup_integration(hass):
    """Set up the integration with mocked Bluetooth transport."""
    entry = _config_entry()
    entry.add_to_hass(hass)
    runtime_device = _runtime_device()
    ble_device = SimpleNamespace(
        address="AA:BB:CC:DD:EE:FF",
        name="NEEWER-GL1 PRO",
    )

    with (
        patch(
            "custom_components.neewer_ble.async_ble_device_from_address",
            return_value=ble_device,
        ),
        patch(
            "custom_components.neewer_ble.NeewerLightDevice",
            return_value=runtime_device,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry, runtime_device


async def test_setup_stores_runtime_data_and_unloads(hass) -> None:
    """Setup should use ConfigEntry runtime data and unload cleanly."""
    entry, runtime_device = await _setup_integration(hass)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is runtime_device
    states = hass.states.async_all("light")
    assert len(states) == 1
    assert states[0].attributes["assumed_state"] is True

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    runtime_device.disconnect.assert_awaited_once()


async def test_setup_retries_when_device_is_not_available(hass) -> None:
    """Setup should ask Home Assistant to retry when no BLEDevice is cached."""
    entry = _config_entry()

    with patch(
        "custom_components.neewer_ble.async_ble_device_from_address",
        return_value=None,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


async def test_failed_light_service_surfaces_home_assistant_error(hass) -> None:
    """A transport failure should fail the light service and retain state."""
    _entry, runtime_device = await _setup_integration(hass)
    runtime_device.turn_on.return_value = False
    state = hass.states.async_all("light")[0]

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": state.entity_id},
            blocking=True,
        )

    assert hass.states.get(state.entity_id).state == "off"


async def test_option_update_uses_runtime_data(hass) -> None:
    """Options should update the device stored on the config entry."""
    entry, runtime_device = await _setup_integration(hass)

    hass.config_entries.async_update_entry(
        entry,
        options={
            "default_brightness": 55,
            "default_color_temp": 5000,
            "keep_connected": True,
        },
    )
    await hass.async_block_till_done()

    runtime_device.set_defaults.assert_called_once_with(55, 5000, True)
