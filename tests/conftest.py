"""Shared Home Assistant fixtures for Neewer BLE tests."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations,
    mock_bluetooth,
):
    """Enable custom integrations with the host Bluetooth stack mocked."""
    with (
        patch("bluetooth_adapters.dbus.unpack_variants", return_value={}),
        patch(
            "bluetooth_adapters.dbus.load_history_from_managed_objects",
            return_value={},
        ),
    ):
        yield
