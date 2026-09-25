"""Protocol tests that do not require Home Assistant or Bluetooth hardware."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "neewer_ble"


def _install_dependency_stubs() -> None:
    """Install the small import surface used by neewer_device."""
    bleak = ModuleType("bleak")
    bleak.BleakClient = object
    bleak.BleakScanner = object
    sys.modules["bleak"] = bleak

    bleak_backends = ModuleType("bleak.backends")
    bleak_device = ModuleType("bleak.backends.device")
    bleak_device.BLEDevice = object
    sys.modules["bleak.backends"] = bleak_backends
    sys.modules["bleak.backends.device"] = bleak_device

    bleak_exc = ModuleType("bleak.exc")
    bleak_exc.BleakError = Exception
    sys.modules["bleak.exc"] = bleak_exc

    retry = ModuleType("bleak_retry_connector")
    retry.establish_connection = AsyncMock()
    retry.BleakClientWithServiceCache = object
    sys.modules["bleak_retry_connector"] = retry


def _load_device_class():
    custom_components = ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    sys.modules["custom_components"] = custom_components

    package = ModuleType("custom_components.neewer_ble")
    package.__path__ = [str(COMPONENT)]
    sys.modules["custom_components.neewer_ble"] = package

    for module_name in ("const", "neewer_device"):
        full_name = f"custom_components.neewer_ble.{module_name}"
        spec = importlib.util.spec_from_file_location(full_name, COMPONENT / f"{module_name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

    return sys.modules["custom_components.neewer_ble.neewer_device"].NeewerLightDevice


_install_dependency_stubs()
NeewerLightDevice = _load_device_class()


class FakeBLEDevice:
    """Minimal BLE device used by the protocol unit tests."""

    address = "AA:BB:CC:DD:EE:FF"

    def __init__(self, name: str) -> None:
        self.name = name


class GL1ProProtocolTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.device = NeewerLightDevice(FakeBLEDevice("NEEWER-GL1 PRO"))

    def test_detects_gl1_pro_capabilities(self) -> None:
        self.assertEqual(self.device.model_name, "GL1 Pro")
        self.assertEqual(self.device.color_temp_range, (2900, 7000))
        self.assertTrue(self.device.is_cct_only)
        self.assertTrue(self.device.uses_power_commands)
        self.assertFalse(self.device.uses_infinity_protocol)

    def test_temperature_commands_use_gl1_pro_range(self) -> None:
        self.assertEqual(self.device._build_temp_only_command(0), [0x78, 0x83, 0x01, 29, 0x19])
        self.assertEqual(self.device._build_temp_only_command(100), [0x78, 0x83, 0x01, 70, 0x42])

    async def test_turn_on_sends_power_brightness_and_temperature(self) -> None:
        self.device._send_command = AsyncMock(return_value=True)

        device_module = sys.modules["custom_components.neewer_ble.neewer_device"]
        with patch.object(device_module.asyncio, "sleep", new=AsyncMock()):
            result = await self.device.turn_on(brightness=60, color_temp_kelvin=4500)

        self.assertTrue(result)
        commands = [call.args for call in self.device._send_command.await_args_list]
        self.assertEqual(
            commands,
            [
                ([0x78, 0x81, 0x01, 0x01, 0xFB],),
                ([0x78, 0x82, 0x01, 60, 0x37],),
                ([0x78, 0x83, 0x01, 45, 0x29],),
            ],
        )
        self.assertTrue(self.device._send_command.await_args_list[0].kwargs["keep_connected"])
        self.assertTrue(self.device._send_command.await_args_list[1].kwargs["keep_connected"])

    async def test_turn_off_uses_explicit_power_command(self) -> None:
        self.device._send_command = AsyncMock(return_value=True)

        result = await self.device.turn_off()

        self.assertTrue(result)
        self.device._send_command.assert_awaited_once_with([0x78, 0x81, 0x01, 0x02, 0xFC])


class BetaDeviceProfileTest(unittest.IsolatedAsyncioTestCase):
    async def test_detects_ms150b_product_name(self) -> None:
        device = NeewerLightDevice(FakeBLEDevice("MS150B-9A785C"))

        self.assertEqual(device.model_name, "MS150B")
        self.assertEqual(device.color_temp_range, (2700, 6500))
        self.assertTrue(device.uses_infinity_protocol)

    async def test_detects_pl60c_product_code(self) -> None:
        device = NeewerLightDevice(FakeBLEDevice("NW-20220016&776A0500"))

        self.assertEqual(device.model_name, "PL60C")
        self.assertEqual(device.color_temp_range, (2500, 10000))
        self.assertTrue(device.supports_rgb)
        self.assertTrue(device.uses_infinity_protocol)

    async def test_detects_ap150c_name(self) -> None:
        device = NeewerLightDevice(FakeBLEDevice("NEEWER-AP150C-2"))

        self.assertEqual(device.model_name, "AP150C")
        self.assertEqual(device.color_temp_range, (2500, 10000))
        self.assertTrue(device.supports_rgb)
        self.assertTrue(device.uses_infinity_protocol)

    async def test_rgb168_does_not_fall_back_to_rgb1(self) -> None:
        device = NeewerLightDevice(FakeBLEDevice("NEEWER-RGB168"))

        self.assertEqual(device.model_name, "RGB168")
        self.assertEqual(device.light_type, 2)
        self.assertEqual(device.color_temp_range, (2500, 8500))
        self.assertEqual(
            device._build_cct_command(50, 0),
            [0x78, 0x87, 0x03, 50, 25, 50, 0x7F],
        )


class ConnectionBehaviorTest(unittest.IsolatedAsyncioTestCase):
    async def test_persistent_connection_stays_open_after_command(self) -> None:
        device = NeewerLightDevice(
            FakeBLEDevice("NEEWER-RGB660"), keep_connected=True
        )
        device.connect = AsyncMock(return_value=True)
        device.disconnect = AsyncMock()
        device._client = type(
            "FakeClient", (), {"write_gatt_char": AsyncMock()}
        )()

        result = await device._send_command([0x78, 0x81, 0x01, 0x01, 0xFB])

        self.assertTrue(result)
        device.disconnect.assert_not_awaited()

    async def test_default_connection_disconnects_after_command(self) -> None:
        device = NeewerLightDevice(FakeBLEDevice("NEEWER-RGB660"))
        device.connect = AsyncMock(return_value=True)
        device.disconnect = AsyncMock()
        device._client = type(
            "FakeClient", (), {"write_gatt_char": AsyncMock()}
        )()

        result = await device._send_command([0x78, 0x81, 0x01, 0x01, 0xFB])

        self.assertTrue(result)
        device.disconnect.assert_awaited_once()

    async def test_persistent_connection_disconnects_after_failed_command(self) -> None:
        device = NeewerLightDevice(
            FakeBLEDevice("NEEWER-RGB660"), keep_connected=True
        )
        device.connect = AsyncMock(return_value=True)
        device.disconnect = AsyncMock()
        device._client = type(
            "FakeClient",
            (),
            {"write_gatt_char": AsyncMock(side_effect=RuntimeError("write failed"))},
        )()

        result = await device._send_command([0x78, 0x81, 0x01, 0x01, 0xFB])

        self.assertFalse(result)
        device.disconnect.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
