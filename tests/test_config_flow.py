"""Tests for the Neewer BLE config flow."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.neewer_ble.config_flow import NeewerBLEConfigFlow
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


async def test_bluetooth_discovery_confirmation_for_ms150b(hass) -> None:
    """MS150B devices advertise without NEEWER/NW- prefixes but should still be discovered."""
    service_info = _service_info(name="MS150B-9A785C")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=service_info,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"


async def test_user_flow_lists_ms150b_from_discovery_cache(hass) -> None:
    """MS150B devices should appear in the manual device picker list."""
    service_info = _service_info(name="MS150B-9A785C")

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

    with patch(
        "custom_components.neewer_ble.async_setup_entry",
        return_value=True,
    ):
        created = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"address": service_info.address},
        )

    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["title"] == "MS150B-9A785C"


def test_is_neewer_device_matches_ms150b() -> None:
    """The Neewer device name filter should recognize MS150B advertised names."""
    assert NeewerBLEConfigFlow._is_neewer_device("MS150B-9A785C") is True
    assert NeewerBLEConfigFlow._is_neewer_device("ms150b-9a785c") is True
    assert NeewerBLEConfigFlow._is_neewer_device("SomeOtherDevice") is False


@pytest.mark.parametrize(
    "address",
    [
        "",
        "not-a-mac",
        "GG:HH:II:JJ:KK:LL",
        "AA:BB:CC:DD:EE:FG",
        "AA:BB:CC:DD:EE",
        "AA:BB:CC:DD:EE:FF:00",
        "A:BB:CC:DD:EE:FFF",
        "AAA:B:CC:DD:EE:FF",
        "AABB::CC:DD:EE:FF",
        ":AA:BB:CC:DD:EEFF",
        "AA:BB:CC:DD:EEFF:",
        " AA:BB:CC:DD:EE:FF",
        "AA:BB:CC:DD:EE:FF ",
        "AA:BB:CC:DD:EE:FF\n",
    ],
)
async def test_manual_flow_rejects_invalid_address(hass, address) -> None:
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
        {"address": address, "name": "Studio light"},
    )

    assert invalid["type"] is FlowResultType.FORM
    assert invalid["step_id"] == "manual"
    assert invalid["errors"] == {"base": "invalid_address"}
    assert hass.config_entries.async_entries(DOMAIN) == []


@pytest.mark.parametrize("address", ["aa:bb:cc:dd:ee:ff", "00:00:00:00:00:00"])
async def test_manual_flow_normalizes_valid_address(hass, address) -> None:
    """Valid manual addresses should use uppercase data and unique IDs."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER},
    )
    manual = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": "manual"}
    )

    with patch("custom_components.neewer_ble.async_setup_entry", return_value=True):
        created = await hass.config_entries.flow.async_configure(
            manual["flow_id"], {"address": address, "name": "Studio light"}
        )

    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["title"] == "Studio light"
    assert created["data"] == {"address": address.upper(), "name": "Studio light"}
    assert created["result"].unique_id == address.upper()


@pytest.mark.parametrize("address", ["AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff"])
async def test_manual_flow_aborts_for_discovered_entry(hass, address) -> None:
    """Manual entry should detect a device already configured by discovery."""
    discovered = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=_service_info(),
    )
    with patch("custom_components.neewer_ble.async_setup_entry", return_value=True):
        created = await hass.config_entries.flow.async_configure(
            discovered["flow_id"], {}
        )
    assert created["type"] is FlowResultType.CREATE_ENTRY

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER},
    )
    manual = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": "manual"}
    )
    duplicate = await hass.config_entries.flow.async_configure(
        manual["flow_id"], {"address": address, "name": "Studio light"}
    )

    assert duplicate["type"] is FlowResultType.ABORT
    assert duplicate["reason"] == "already_configured"
    assert hass.config_entries.async_entries(DOMAIN) == [created["result"]]
