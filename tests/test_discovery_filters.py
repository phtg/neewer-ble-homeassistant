"""Keep the manifest and config flow discovery name filters in agreement."""

import ast
from fnmatch import fnmatchcase
import inspect
import json
from pathlib import Path
import textwrap

import pytest

from custom_components.neewer_ble.config_flow import NeewerBLEConfigFlow
from custom_components.neewer_ble.const import SUPPORTED_MODELS


@pytest.fixture
def local_name_globs() -> list[str]:
    """Read the actual matchers rather than duplicating them in the test."""
    path = (
        Path(__file__).resolve().parents[1]
        / "custom_components/neewer_ble/manifest.json"
    )
    with path.open(encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    return [matcher["local_name"] for matcher in manifest["bluetooth"]]


def _manifest_matches(name: str | None, patterns: list[str]) -> bool:
    """Apply Home Assistant's case-insensitive, fnmatch-style name matching."""
    return bool(name) and any(
        fnmatchcase(name.lower(), pattern.lower()) for pattern in patterns
    )


def test_discovery_filters_agree(local_name_globs) -> None:
    """Probe both sources so a prefix added to either alone is detected."""
    source = textwrap.dedent(inspect.getsource(NeewerBLEConfigFlow._is_neewer_device))
    flow_prefixes = {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    # Include new flow string literals automatically (also harmlessly includes
    # the docstring). Manifest matchers currently have a literal prefix and '*'.
    manifest_prefixes = set()
    for pattern in local_name_globs:
        assert pattern.endswith("*") and not any(
            char in pattern[:-1] for char in "*?[]"
        ), "Extend the discovery probes for this new glob shape"
        manifest_prefixes.add(pattern[:-1])

    names = {None, "", "0", "OtherDevice", "NW", "MS150", "NEEWE"}
    for prefix in flow_prefixes | manifest_prefixes:
        for suffix in ("", "0", "-RGB660", "-MS150B", "&000000"):
            name = prefix + suffix
            names.update((name, name.lower(), name.swapcase(), "Other-" + name))

    for name in names:
        assert NeewerBLEConfigFlow._is_neewer_device(name) == _manifest_matches(
            name, local_name_globs
        ), f"Discovery filters disagree for {name!r}"


@pytest.mark.parametrize("model_code", SUPPORTED_MODELS)
@pytest.mark.parametrize("lowercase", [False, True])
def test_supported_model_name_shapes(model_code, lowercase, local_name_globs) -> None:
    """Cover the documented prefixed shapes, including numeric aliases."""
    if model_code.isdecimal():
        names = [f"NW-{model_code}&000000"]
    else:
        names = [f"NEEWER-{model_code}"]
        if model_code == "MS150B":
            names.append("MS150B-000000")
        if model_code == "GL1PRO":
            names.append("NEEWER-GL1 PRO")

    for name in names:
        if lowercase:
            name = name.lower()
        assert NeewerBLEConfigFlow._is_neewer_device(name), name
        assert _manifest_matches(name, local_name_globs), name
