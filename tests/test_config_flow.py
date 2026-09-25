"""Tests for the Neewer BLE config flow."""

from types import SimpleNamespace
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.neewer_ble.const import DOMAIN


def _service_info(name: str = "NEEWER-GL1 PRO") -> SimpleNamespace:
    """Create Bluetooth discovery data for a Neewer light."""
    device = SimpleNamespace(address="AA:BB:CC:DD:EE:FF", name=name)
    return SimpleNamespace(
        address=device.address,
        name=name,
        device=device,
    )


async def test_user_flow_uses_home_assistant_discovery_cache(hass) -> None:
    """User setup should list devices from Home Assistant's shared scanner."""
    service_info = _service_info()

    with patch(
        "custom_components.neewer_ble.config_flow.async_discovered_service_info",
        return_value=[service_info],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "custom_components.neewer_ble.async_setup_entry",
        return_value=True,
    ):
        created = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"address": service_info.address},
        )

    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["title"] == "NEEWER-GL1 PRO"
    assert created["data"] == {
        "address": "AA:BB:CC:DD:EE:FF",
        "name": "NEEWER-GL1 PRO",
    }


async def test_bluetooth_discovery_confirmation(hass) -> None:
    """Manifest Bluetooth discovery should create a confirm-only flow."""
    service_info = _service_info()

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=service_info,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch(
        "custom_components.neewer_ble.async_setup_entry",
        return_value=True,
    ):
        created = await hass.config_entries.flow.async_configure(
            result["flow_id"], {}
        )

    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["data"]["address"] == service_info.address


async def test_manual_flow_rejects_invalid_address(hass) -> None:
    """Manual setup should validate Bluetooth MAC address formatting."""
    with patch(
        "custom_components.neewer_ble.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )

    manual = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": "manual"}
    )
    invalid = await hass.config_entries.flow.async_configure(
        manual["flow_id"],
        {"address": "not-a-mac", "name": "Studio light"},
    )

    assert invalid["type"] is FlowResultType.FORM
    assert invalid["errors"] == {"base": "invalid_address"}
