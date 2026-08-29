"""Manage the skill files bundled with the OPERA ecosystem."""

from __future__ import annotations

import shutil
import warnings
from importlib import metadata, resources
from pathlib import Path

# ---------------------------------------------------------------------------
# Project constants
# ---------------------------------------------------------------------------

SKILL_PACKAGE = "opera.skills"

# Map each short name to the Markdown file bundled with the package.
SKILL_FILES: dict[str, str] = {
    "opera": "opera.md",
    "bvar": "bvar.md",
    "forecast-combo": "forecast_combo.md",
    "forecast-decomp": "news_decomp.md",
    "forecast-evaluation": "forecast_evaluation.md",
    "forecast-realtime": "forecast_realtime.md",
    "nowcast-midas": "nowcast_midas.md",
}

# Default installation targets, in priority order.
DEFAULT_TARGETS = [
    ".claude/skills",  # Claude Code
    ".github/skills",  # GitHub Copilot skills
]


class SkillVersionWarning(UserWarning):
    """The installed package differs from the version described by a skill."""


def _skills_source_dir() -> Path:
    """Return the directory that contains the bundled skill files."""
    ref = resources.files(SKILL_PACKAGE)
    # Convert the package resource reference to the path used by this module.
    return Path(str(ref))


def list_skills() -> list[dict[str, str]]:
    """Return metadata for each bundled skill.

    Each dictionary contains the skill ``name``, its ``filename``, and the
    short ``description`` read from the skill file.
    """
    src = _skills_source_dir()
    result = []
    for name, filename in sorted(SKILL_FILES.items()):
        filepath = src / filename
        description = ""
        if filepath.exists():
            for line in filepath.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("description:"):
                    description = stripped.split(":", 1)[1].strip()
                    break
        result.append({"name": name, "filename": filename, "description": description})
    return result


def show_skill(name: str) -> str:
    """Return the complete skill text for a short name."""
    if name not in SKILL_FILES:
        available = ", ".join(sorted(SKILL_FILES))
        raise KeyError(f"Unknown skill {name!r}. Available: {available}")
    src = _skills_source_dir() / SKILL_FILES[name]
    return src.read_text(encoding="utf-8")


def install_skills(
    target: str | Path | None = None,
    skills: list[str] | None = None,
) -> Path:
    """Copy selected skill files to the *target* directory.

    Parameters
    ----------
    target : str | Path | None
        Destination directory. When ``None``, use the first default target
        whose parent exists. If no parent exists, use ``.claude/skills``.
    skills : list[str] | None
        Short names to install. ``None`` installs every bundled skill.

    Returns
    -------
    Path
        The directory the skills were installed to.

    Raises
    ------
    KeyError
        If ``skills`` contains an unknown skill name.
    """
    if target is None:
        target_path = _resolve_default_target()
    else:
        target_path = Path(target)

    target_path.mkdir(parents=True, exist_ok=True)

    src_dir = _skills_source_dir()
    names = skills if skills else list(SKILL_FILES)

    for name in names:
        if name not in SKILL_FILES:
            available = ", ".join(sorted(SKILL_FILES))
            raise KeyError(f"Unknown skill {name!r}. Available: {available}")
        src_file = src_dir / SKILL_FILES[name]
        _warn_if_stale_skill(name, src_file)
        # Keep each skill in its own <target>/<skill-name> directory.
        skill_dir = target_path / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, skill_dir / "SKILL.md")

    return target_path


def _read_generated_fields(text: str) -> dict[str, str]:
    """Read the generated package and version fields from initial front matter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if separator and key.strip() in {"module-package", "module-version"}:
            fields[key.strip()] = value.strip().strip('"')
    return fields


def _warn_if_stale_skill(name: str, source: Path) -> None:
    fields = _read_generated_fields(source.read_text(encoding="utf-8"))
    package = fields.get("module-package")
    described_version = fields.get("module-version")
    if not package or not described_version:
        return
    try:
        installed_version = metadata.version(package)
    except metadata.PackageNotFoundError:
        installed_version = "not installed"
    except Exception:  # noqa: BLE001
        installed_version = "not installed"
    if installed_version != described_version:
        warnings.warn(
            f"Skill {name!r} describes {package} {described_version}; "
            f"installed version: {installed_version}.",
            SkillVersionWarning,
            stacklevel=2,
        )


def _resolve_default_target() -> Path:
    """Return the first default directory with an existing parent."""
    cwd = Path.cwd()
    for candidate in DEFAULT_TARGETS:
        parent = (cwd / candidate).parent
        if parent.exists():
            return cwd / candidate
    # Use the first target when none of its parents exists yet.
    return cwd / DEFAULT_TARGETS[0]
