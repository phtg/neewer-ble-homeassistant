"""Light entity behavior tests with small Home Assistant stubs."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock


ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components" / "neewer_ble"


def _install_home_assistant_stubs() -> None:
    homeassistant = ModuleType("homeassistant")
    components = ModuleType("homeassistant.components")
    light = ModuleType("homeassistant.components.light")
    light.ATTR_BRIGHTNESS = "brightness"
    light.ATTR_COLOR_TEMP_KELVIN = "color_temp_kelvin"
    light.ATTR_HS_COLOR = "hs_color"
    light.ColorMode = SimpleNamespace(COLOR_TEMP="color_temp", HS="hs")

    class LightEntity:
        def async_write_ha_state(self) -> None:
            pass

    light.LightEntity = LightEntity
    light.LightEntityFeature = object

    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    const = ModuleType("homeassistant.const")
    const.CONF_ADDRESS = "address"
    const.CONF_NAME = "name"
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object

    helpers = ModuleType("homeassistant.helpers")
    device_registry = ModuleType("homeassistant.helpers.device_registry")
    device_registry.DeviceInfo = dict
    entity_platform = ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = object

    modules = {
        "homeassistant": homeassistant,
        "homeassistant.components": components,
        "homeassistant.components.light": light,
        "homeassistant.config_entries": config_entries,
        "homeassistant.const": const,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.device_registry": device_registry,
        "homeassistant.helpers.entity_platform": entity_platform,
    }
    sys.modules.update(modules)


def _load_light_class():
    _install_home_assistant_stubs()

    if "custom_components.neewer_ble.const" not in sys.modules:
        custom_components = ModuleType("custom_components")
        custom_components.__path__ = [str(ROOT / "custom_components")]
        sys.modules["custom_components"] = custom_components

        package = ModuleType("custom_components.neewer_ble")
        package.__path__ = [str(COMPONENT)]
        sys.modules["custom_components.neewer_ble"] = package

        full_name = "custom_components.neewer_ble.const"
        spec = importlib.util.spec_from_file_location(full_name, COMPONENT / "const.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)

        device_module = ModuleType("custom_components.neewer_ble.neewer_device")
        device_module.NeewerLightDevice = object
        sys.modules["custom_components.neewer_ble.neewer_device"] = device_module

    full_name = "custom_components.neewer_ble.light"
    spec = importlib.util.spec_from_file_location(full_name, COMPONENT / "light.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.NeewerBLELight, sys.modules["homeassistant.components.light"]


NeewerBLELight, ha_light = _load_light_class()


class FakeDevice:
    address = "AA:BB:CC:DD:EE:FF"
    name = "NEEWER-CB100C"
    model_name = "CB100C"
    supports_rgb = True
    color_temp_range = (2500, 10000)
    hue = 280
    saturation = 75
    brightness = 60
    color_temp_kelvin = 4500
    is_on = True
    set_rgb = AsyncMock(return_value=True)
    turn_on = AsyncMock(return_value=True)


class FakeEntry:
    data = {"name": "Studio light"}


class LightModeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.device = FakeDevice()
        self.device.set_rgb = AsyncMock(return_value=True)
        self.device.turn_on = AsyncMock(return_value=True)
        self.entity = NeewerBLELight(self.device, FakeEntry())

    async def test_brightness_only_update_preserves_hs_mode(self) -> None:
        self.entity._attr_color_mode = ha_light.ColorMode.HS

        await self.entity.async_turn_on(brightness=128)

        self.device.set_rgb.assert_awaited_once_with(
            hue=280,
            saturation=75,
            brightness=50,
        )
        self.device.turn_on.assert_not_awaited()

    async def test_explicit_color_temperature_switches_to_cct(self) -> None:
        self.entity._attr_color_mode = ha_light.ColorMode.HS

        await self.entity.async_turn_on(color_temp_kelvin=5000)

        self.device.turn_on.assert_awaited_once_with(
            brightness=None,
            color_temp_kelvin=5000,
        )
        self.assertEqual(self.entity._attr_color_mode, ha_light.ColorMode.COLOR_TEMP)


if __name__ == "__main__":
    unittest.main()
