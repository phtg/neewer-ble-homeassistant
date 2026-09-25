"""Tests for Neewer BLE protocol and connection behavior."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.neewer_ble.neewer_device import NeewerLightDevice


def _ble_device(name: str = "NEEWER-GL1 PRO") -> SimpleNamespace:
    """Create the BLEDevice surface used by the protocol class."""
    return SimpleNamespace(address="AA:BB:CC:DD:EE:FF", name=name)


def test_detects_gl1_pro_capabilities() -> None:
    """GL1 Pro should select its hardware-tested protocol profile."""
    device = NeewerLightDevice(_ble_device())

    assert device.model_name == "GL1 Pro"
    assert device.color_temp_range == (2900, 7000)
    assert device.is_cct_only
    assert device.uses_power_commands
    assert not device.uses_infinity_protocol


def test_temperature_commands_use_gl1_pro_range() -> None:
    """GL1 Pro temperature packets should use its 2900-7000 K range."""
    device = NeewerLightDevice(_ble_device())

    assert device._build_temp_only_command(0) == [0x78, 0x83, 0x01, 29, 0x19]
    assert device._build_temp_only_command(100) == [
        0x78,
        0x83,
        0x01,
        70,
        0x42,
    ]


async def test_turn_on_sends_power_brightness_and_temperature() -> None:
    """GL1 Pro turn-on should send its three-command sequence."""
    device = NeewerLightDevice(_ble_device())
    device._send_command = AsyncMock(return_value=True)

    with patch(
        "custom_components.neewer_ble.neewer_device.asyncio.sleep",
        new=AsyncMock(),
    ):
        result = await device.turn_on(brightness=60, color_temp_kelvin=4500)

    assert result
    commands = [call.args for call in device._send_command.await_args_list]
    assert commands == [
        ([0x78, 0x81, 0x01, 0x01, 0xFB],),
        ([0x78, 0x82, 0x01, 60, 0x37],),
        ([0x78, 0x83, 0x01, 45, 0x29],),
    ]
    assert device._send_command.await_args_list[0].kwargs["keep_connected"]
    assert device._send_command.await_args_list[1].kwargs["keep_connected"]
    assert device.is_on
    assert device.brightness == 60
    assert abs(device.color_temp_kelvin - 4500) <= 1


async def test_turn_on_failure_preserves_assumed_state() -> None:
    """A failed command sequence must not claim the requested state."""
    device = NeewerLightDevice(_ble_device())
    original_temperature = device.color_temp_kelvin
    device._send_command = AsyncMock(return_value=False)

    result = await device.turn_on(brightness=25, color_temp_kelvin=6000)

    assert not result
    assert not device.is_on
    assert device.brightness == 100
    assert device.color_temp_kelvin == original_temperature


async def test_turn_off_uses_explicit_power_command() -> None:
    """GL1 Pro should use the explicit power-off packet."""
    device = NeewerLightDevice(_ble_device())
    device._is_on = True
    device._send_command = AsyncMock(return_value=True)

    result = await device.turn_off()

    assert result
    device._send_command.assert_awaited_once_with(
        [0x78, 0x81, 0x01, 0x02, 0xFC]
    )
    assert not device.is_on


async def test_turn_off_failure_preserves_assumed_state() -> None:
    """A failed power-off command must leave the entity logically on."""
    device = NeewerLightDevice(_ble_device())
    device._is_on = True
    device._send_command = AsyncMock(return_value=False)

    result = await device.turn_off()

    assert not result
    assert device.is_on


def test_detects_beta_device_profiles() -> None:
    """Beta model identifiers should select their intended profiles."""
    cases = (
        ("MS150B-9A785C", "MS150B", (2700, 6500), False, 1),
        ("NW-20220016&776A0500", "PL60C", (2500, 10000), True, 1),
        ("NEEWER-AP150C-2", "AP150C", (2500, 10000), True, 1),
        ("NEEWER-RGB168", "RGB168", (2500, 8500), True, 2),
    )

    for name, model, cct_range, rgb, light_type in cases:
        device = NeewerLightDevice(_ble_device(name))
        assert device.model_name == model
        assert device.color_temp_range == cct_range
        assert device.supports_rgb is rgb
        assert device.light_type == light_type


def test_rgb168_does_not_fall_back_to_rgb1() -> None:
    """The longest model match should win for RGB168."""
    device = NeewerLightDevice(_ble_device("NEEWER-RGB168"))

    assert device._build_cct_command(50, 0) == [
        0x78,
        0x87,
        0x03,
        50,
        25,
        50,
        0x7F,
    ]


async def test_persistent_connection_stays_open_after_command() -> None:
    """Persistent mode should retain a healthy connection."""
    device = NeewerLightDevice(_ble_device("NEEWER-RGB660"), keep_connected=True)
    device.connect = AsyncMock(return_value=True)
    device.disconnect = AsyncMock()
    device._client = SimpleNamespace(write_gatt_char=AsyncMock())

    result = await device._send_command([0x78, 0x81, 0x01, 0x01, 0xFB])

    assert result
    device.disconnect.assert_not_awaited()


async def test_default_connection_disconnects_after_command() -> None:
    """Default mode should release the Bluetooth connection after a write."""
    device = NeewerLightDevice(_ble_device("NEEWER-RGB660"))
    device.connect = AsyncMock(return_value=True)
    device.disconnect = AsyncMock()
    device._client = SimpleNamespace(write_gatt_char=AsyncMock())

    result = await device._send_command([0x78, 0x81, 0x01, 0x01, 0xFB])

    assert result
    device.disconnect.assert_awaited_once()


async def test_persistent_connection_disconnects_after_failed_command() -> None:
    """A failed write should always discard the connection."""
    device = NeewerLightDevice(_ble_device("NEEWER-RGB660"), keep_connected=True)
    device.connect = AsyncMock(return_value=True)
    device.disconnect = AsyncMock()
    device._client = SimpleNamespace(
        write_gatt_char=AsyncMock(side_effect=RuntimeError("write failed"))
    )

    result = await device._send_command([0x78, 0x81, 0x01, 0x01, 0xFB])

    assert not result
    device.disconnect.assert_awaited_once()


async def test_connection_uses_fresh_ble_device_callback() -> None:
    """The retry connector should receive Home Assistant's refresh callback."""
    initial_device = _ble_device()
    refreshed_device = _ble_device()
    callback = lambda: refreshed_device
    connected_client = SimpleNamespace(is_connected=True)
    device = NeewerLightDevice(
        initial_device,
        ble_device_callback=callback,
    )

    with patch(
        "custom_components.neewer_ble.neewer_device.establish_connection",
        new=AsyncMock(return_value=connected_client),
    ) as establish:
        assert await device.connect()

    assert establish.await_args.kwargs["ble_device_callback"] is callback


async def test_rgb_failure_preserves_color_state() -> None:
    """Failed RGB writes should not change the assumed color."""
    device = NeewerLightDevice(_ble_device("NEEWER-RGB660"))
    device._send_command = AsyncMock(return_value=False)

    result = await device.set_rgb(280, 75, 40)

    assert not result
    assert device.hue == 0
    assert device.saturation == 100
    assert device.brightness == 100
    assert not device.is_on
