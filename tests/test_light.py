"""Tests for the Neewer light entity."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
)
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


@pytest.mark.parametrize(
    "brightness, expected",
    [(0, 0), (1, 1), (2, 1), (128, 50), (255, 100), (None, None)],
)
@pytest.mark.parametrize("mode", ["cct", "explicit_cct", "hs", "explicit_hs"])
async def test_turn_on_brightness_scaling(brightness, expected, mode) -> None:
    """Scale brightness in every color path, preserving omitted brightness."""
    entity, device = _entity()
    kwargs = {} if brightness is None else {ATTR_BRIGHTNESS: brightness}
    if mode == "explicit_cct":
        entity._attr_color_mode = ColorMode.HS
        kwargs[ATTR_COLOR_TEMP_KELVIN] = 5000
    elif mode == "hs":
        entity._attr_color_mode = ColorMode.HS
    elif mode == "explicit_hs":
        kwargs[ATTR_HS_COLOR] = (120, 40)

    await entity.async_turn_on(**kwargs)

    if mode in ("hs", "explicit_hs"):
        device.set_rgb.assert_awaited_once_with(
            hue=120 if mode == "explicit_hs" else 280,
            saturation=40 if mode == "explicit_hs" else 75,
            brightness=expected,
        )
        device.turn_on.assert_not_awaited()
    else:
        device.turn_on.assert_awaited_once_with(
            brightness=expected,
            color_temp_kelvin=5000 if mode == "explicit_cct" else None,
        )
        device.set_rgb.assert_not_awaited()


@pytest.mark.parametrize("brightness, expected", [(0, 0), (50, 128), (100, 255)])
def test_brightness_property_scaling(brightness, expected) -> None:
    """Report rounded Home Assistant brightness including both endpoints."""
    entity, device = _entity()
    device.brightness = brightness

    assert entity.brightness == expected


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


async def test_rapid_updates_skip_superseded_pending_commands() -> None:
    """Only the newest slider update should run after an active command."""
    entity, device = _entity()
    entity._attr_color_mode = ColorMode.COLOR_TEMP
    first_command_started = asyncio.Event()
    release_first_command = asyncio.Event()
    sent_brightness: list[int | None] = []

    async def _turn_on(*, brightness, color_temp_kelvin) -> bool:
        sent_brightness.append(brightness)
        if len(sent_brightness) == 1:
            first_command_started.set()
            await release_first_command.wait()
        return True

    device.turn_on.side_effect = _turn_on

    first = asyncio.create_task(
        entity.async_turn_on(**{ATTR_BRIGHTNESS: 51})
    )
    await first_command_started.wait()

    superseded = asyncio.create_task(
        entity.async_turn_on(**{ATTR_BRIGHTNESS: 102})
    )
    await asyncio.sleep(0)
    latest = asyncio.create_task(
        entity.async_turn_on(**{ATTR_BRIGHTNESS: 204})
    )
    await asyncio.sleep(0)

    release_first_command.set()
    await asyncio.gather(first, superseded, latest)

    assert sent_brightness == [20, 80]
    assert entity.async_write_ha_state.call_count == 1
