"""Tests for the Neewer light entity."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode
from homeassistant.exceptions import HomeAssistantError

from custom_components.neewer_ble.light import NeewerBLELight


def _device() -> SimpleNamespace:
    """Create the runtime device surface used by the light entity."""
    return SimpleNamespace(
        address="AA:BB:CC:DD:EE:FF",
        name="NEEWER-CB100C",
        model_name="CB100C",
        supports_rgb=True,
        uses_infinity_protocol=True,
        color_temp_range=(2500, 10000),
        hue=280,
        saturation=75,
        brightness=60,
        color_temp_kelvin=4500,
        is_on=True,
        set_rgb=AsyncMock(return_value=True),
        turn_on=AsyncMock(return_value=True),
        turn_off=AsyncMock(return_value=True),
    )


def _entity() -> tuple[NeewerBLELight, SimpleNamespace]:
    """Create a detached entity with state writes mocked."""
    device = _device()
    entry = SimpleNamespace(data={"name": "Studio light"})
    entity = NeewerBLELight(device, entry)
    entity.async_write_ha_state = Mock()
    return entity, device


async def test_brightness_only_update_preserves_hs_mode() -> None:
    """Brightness-only updates should retain the current RGB color."""
    entity, device = _entity()
    entity._attr_color_mode = ColorMode.HS

    await entity.async_turn_on(**{ATTR_BRIGHTNESS: 128})

    device.set_rgb.assert_awaited_once_with(
        hue=280,
        saturation=75,
        brightness=50,
    )
    device.turn_on.assert_not_awaited()
    assert entity.color_mode is ColorMode.HS
    entity.async_write_ha_state.assert_called_once()


async def test_explicit_color_temperature_switches_to_cct() -> None:
    """An explicit temperature should switch an RGB entity to CCT mode."""
    entity, device = _entity()
    entity._attr_color_mode = ColorMode.HS

    await entity.async_turn_on(color_temp_kelvin=5000)

    device.turn_on.assert_awaited_once_with(
        brightness=None,
        color_temp_kelvin=5000,
    )
    assert entity.color_mode is ColorMode.COLOR_TEMP


async def test_failed_turn_on_raises_and_does_not_publish_state() -> None:
    """Home Assistant should surface a failed Bluetooth command."""
    entity, device = _entity()
    entity._attr_color_mode = ColorMode.HS
    device.set_rgb.return_value = False

    with pytest.raises(HomeAssistantError) as error:
        await entity.async_turn_on(**{ATTR_BRIGHTNESS: 128})

    assert error.value.translation_domain == "neewer_ble"
    assert error.value.translation_key == "command_failed"
    assert entity.color_mode is ColorMode.HS
    entity.async_write_ha_state.assert_not_called()


async def test_failed_turn_off_raises_and_does_not_publish_state() -> None:
    """A failed power-off command should be visible to automations and users."""
    entity, device = _entity()
    device.turn_off.return_value = False

    with pytest.raises(HomeAssistantError):
        await entity.async_turn_off()

    entity.async_write_ha_state.assert_not_called()
