from __future__ import annotations

import json
import types
from importlib import resources
from pathlib import Path

import pytest

from opera import skill_api
from opera.cli import build_parser
from opera.skill_api import (
    SKILL_API_SPECS,
    SkillApiSpec,
    collect_api,
    load_expected_versions,
    sync_api_sections,
    update_skill_text,
    validate_installed_versions,
)
from opera.skills_manager import SKILL_FILES, SKILL_PACKAGE

pytestmark = pytest.mark.contract

_BEGIN = "<!-- BEGIN GENERATED API -->"
_END = "<!-- END GENERATED API -->"


def _resource_text(filename: str) -> str:
    return resources.files(SKILL_PACKAGE).joinpath(filename).read_text(encoding="utf-8")


def _generated_api(text: str) -> dict[str, object]:
    start = text.index(_BEGIN) + len(_BEGIN)
    end = text.index(_END, start)
    payload = text[start:end].split("```json\n", 1)[1].rsplit("\n```", 1)[0]
    return json.loads(payload)


def _front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines[0] == "---"
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if separator:
            fields[key] = value.strip().strip('"')
    return fields


def test_api_manifest_matches_skill_manifest() -> None:
    assert set(SKILL_API_SPECS) == set(SKILL_FILES)
    assert len(SKILL_API_SPECS) == 7
    assert "sc-midas" not in SKILL_API_SPECS


def test_module_requirements_are_exact_pins() -> None:
    expected = load_expected_versions(Path("pyproject.toml"))
    assert set(expected) == {
        "opera-eco",
        "bvar",
        "forecast-combo",
        "forecast-evaluation",
        "forecast-realtime",
        "news-decomp",
        "nowcast-midas",
    }


def test_installed_versions_match_manifest() -> None:
    validate_installed_versions(load_expected_versions(Path("pyproject.toml")))


def test_skill_frontmatter_declares_package_and_version() -> None:
    expected = load_expected_versions(Path("pyproject.toml"))
    for skill_name, filename in SKILL_FILES.items():
        fields = _front_matter(_resource_text(filename))
        spec = SKILL_API_SPECS[skill_name]
        assert fields["module-package"] == spec.package
        assert fields["module-version"] == expected[spec.package.replace("_", "-")]


def test_generated_api_is_valid_json() -> None:
    for filename in SKILL_FILES.values():
        api = _generated_api(_resource_text(filename))
        assert set(api) == {"exports", "package", "signatures", "version"}
        assert isinstance(api["exports"], dict)
        assert isinstance(api["signatures"], dict)


def test_generated_api_matches_installed_packages() -> None:
    for skill_name, spec in SKILL_API_SPECS.items():
        assert _generated_api(_resource_text(SKILL_FILES[skill_name])) == collect_api(
            spec
        )


def test_sync_api_is_idempotent(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    for filename in SKILL_FILES.values():
        source = resources.files(SKILL_PACKAGE).joinpath(filename)
        (skills_dir / filename).write_bytes(source.read_bytes())
    first = sync_api_sections(skills_dir, Path("pyproject.toml"))
    after_first = {path: path.read_bytes() for path in skills_dir.iterdir()}
    second = sync_api_sections(skills_dir, Path("pyproject.toml"))
    assert first == []
    assert second == []
    assert after_first == {path: path.read_bytes() for path in skills_dir.iterdir()}


def test_collect_api_requires_all(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("fake_missing_all")
    monkeypatch.setattr(skill_api.importlib, "import_module", lambda _name: module)
    with pytest.raises(ValueError, match="no __all__"):
        collect_api(SkillApiSpec("fake", ("fake_missing_all",)))


def test_collect_api_requires_export(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("fake_missing_export")
    module.__all__ = ["missing"]
    monkeypatch.setattr(skill_api.importlib, "import_module", lambda _name: module)
    with pytest.raises(ValueError, match="is missing"):
        collect_api(SkillApiSpec("fake", ("fake_missing_export",)))


def test_update_skill_text_rejects_duplicate_markers() -> None:
    text = "---\nname: fake\n---\n" + _BEGIN + "\n" + _END + "\n" + _BEGIN
    with pytest.raises(ValueError, match="exactly one"):
        update_skill_text(text, SkillApiSpec("fake", ("fake",)), {"version": "1"})


def test_collect_api_rejects_uninspectable_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = types.ModuleType("fake_uninspectable")
    module.__all__ = ["function"]
    module.function = lambda: None
    monkeypatch.setattr(skill_api.importlib, "import_module", lambda _name: module)
    monkeypatch.setattr(
        skill_api.inspect,
        "signature",
        lambda _value: (_ for _ in ()).throw(TypeError()),
    )
    with pytest.raises(ValueError, match="Cannot inspect"):
        collect_api(SkillApiSpec("fake", ("fake_uninspectable",)))


def test_validate_installed_versions_reports_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(skill_api.importlib.metadata, "version", lambda _name: "2.0")
    with pytest.raises(RuntimeError, match="expected 1.0, installed 2.0"):
        validate_installed_versions({"fake": "1.0"})


def test_cli_preserves_skill_commands_and_adds_sync_api() -> None:
    parser = build_parser()

    assert parser.parse_args(["install", "skills"]).install_target == "skills"
    assert parser.parse_args(["list", "skills"]).list_target == "skills"
    assert parser.parse_args(["show", "skill", "bvar"]).name == "bvar"
    assert parser.parse_args(["skills", "sync-api"]).skills_command == "sync-api"
