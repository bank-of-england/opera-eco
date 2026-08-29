import warnings
from importlib import resources
from pathlib import Path

import pytest

from opera.skills_manager import (
    SKILL_FILES,
    SKILL_PACKAGE,
    SkillVersionWarning,
    install_skills,
    list_skills,
    show_skill,
)

pytestmark = pytest.mark.contract

CANONICAL_SKILL_FILES = {
    "opera": "opera.md",
    "bvar": "bvar.md",
    "forecast-combo": "forecast_combo.md",
    "forecast-decomp": "news_decomp.md",
    "forecast-evaluation": "forecast_evaluation.md",
    "forecast-realtime": "forecast_realtime.md",
    "nowcast-midas": "nowcast_midas.md",
}


def _front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---"

    try:
        end = lines.index("---", 1)
    except ValueError:
        pytest.fail("skill is missing its closing front matter delimiter")

    fields = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def test_skill_manifest_has_canonical_keys_and_resources() -> None:
    assert len(SKILL_FILES) == 7
    assert set(SKILL_FILES) == set(CANONICAL_SKILL_FILES)
    assert "sc-midas" not in SKILL_FILES
    assert SKILL_FILES["nowcast-midas"] == "nowcast_midas.md"

    source_dir = resources.files(SKILL_PACKAGE)
    for name, filename in SKILL_FILES.items():
        resource = source_dir.joinpath(filename)
        assert resource.is_file(), f"missing resource for {name}: {filename}"

        source_text = resource.read_text(encoding="utf-8")
        front_matter = _front_matter(source_text)
        assert front_matter.get("name")
        assert front_matter.get("description")
        assert show_skill(name) == source_text

    nowcast_text = show_skill("nowcast-midas")
    assert _front_matter(nowcast_text)["name"] == "nowcast-midas"


def test_list_skills_reports_canonical_names_and_filenames() -> None:
    listed = {(skill["name"], skill["filename"]) for skill in list_skills()}

    assert listed == set(CANONICAL_SKILL_FILES.items())


def test_install_nowcast_midas_preserves_source_text(tmp_path: Path) -> None:
    source_text = show_skill("nowcast-midas")
    target = tmp_path / "skills"

    installed_target = install_skills(target, skills=["nowcast-midas"])

    assert installed_target == target
    installed_file = target / "nowcast-midas" / "SKILL.md"
    assert installed_file.read_text(encoding="utf-8") == source_text


def test_sc_midas_lookup_raises_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown skill"):
        show_skill("sc-midas")


def test_matching_skill_version_does_not_warn(tmp_path: Path) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        install_skills(tmp_path, skills=["bvar"])

    assert not [
        warning for warning in caught if warning.category is SkillVersionWarning
    ]


def test_mismatched_skill_version_warns_and_copies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from opera import skills_manager

    monkeypatch.setattr(skills_manager.metadata, "version", lambda _package: "0.0.0")
    with pytest.warns(SkillVersionWarning, match="bvar"):
        install_skills(tmp_path, skills=["bvar"])

    assert (tmp_path / "bvar" / "SKILL.md").is_file()


def test_missing_skill_distribution_warns_and_copies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from opera import skills_manager

    def missing(_package: str) -> str:
        raise skills_manager.metadata.PackageNotFoundError("bvar")

    monkeypatch.setattr(skills_manager.metadata, "version", missing)
    with pytest.warns(SkillVersionWarning, match="not installed"):
        install_skills(tmp_path, skills=["bvar"])

    assert (tmp_path / "bvar" / "SKILL.md").is_file()
