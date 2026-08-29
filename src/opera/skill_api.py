"""Synchronize generated API sections in the bundled skill documents."""

from __future__ import annotations

import importlib
import importlib.metadata
import inspect
import json
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillApiSpec:
    """Describe the package modules represented by one skill."""

    package: str
    modules: tuple[str, ...]


SKILL_API_SPECS: dict[str, SkillApiSpec] = {
    "opera": SkillApiSpec("opera-eco", ("opera",)),
    "bvar": SkillApiSpec(
        "bvar", ("bvar", "bvar.models", "bvar.forecast", "bvar.plots")
    ),
    "forecast-combo": SkillApiSpec(
        "forecast_combo", ("forecast_combo", "forecast_combo.combinations")
    ),
    "forecast-evaluation": SkillApiSpec(
        "forecast_evaluation",
        (
            "forecast_evaluation",
            "forecast_evaluation.tests",
            "forecast_evaluation.visualisations",
            "forecast_evaluation.core",
        ),
    ),
    "forecast-realtime": SkillApiSpec(
        "forecast_realtime", ("forecast_realtime", "forecast_realtime.models")
    ),
    "forecast-decomp": SkillApiSpec("news_decomp", ("news_decomp",)),
    "nowcast-midas": SkillApiSpec(
        "nowcast-midas",
        (
            "nowcast_midas",
            "nowcast_midas.temporal_weights",
            "nowcast_midas.combo_weights",
            "nowcast_midas.utils",
        ),
    ),
}

_REQUIREMENT = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[(?P<extra>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\])?"
    r"\s*==\s*(?P<version>[A-Za-z0-9][A-Za-z0-9.!+_-]*)\s*$"
)
_BEGIN_MARKER = "<!-- BEGIN GENERATED API -->"
_END_MARKER = "<!-- END GENERATED API -->"


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_expected_versions(pyproject_path: Path) -> dict[str, str]:
    """Load the project and exact module versions from ``pyproject.toml``."""
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data["project"]
        project_name = project["name"]
        project_version = project["version"]
        requirements = project["optional-dependencies"]["modules"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid project module manifest: {exc}") from exc

    if not isinstance(project_name, str) or not isinstance(project_version, str):
        raise TypeError("Project name and version must be strings")
    if not isinstance(requirements, list):
        raise TypeError("The project module extra must be a list")

    parsed: dict[str, str] = {}
    for requirement in requirements:
        if not isinstance(requirement, str):
            raise TypeError(f"Invalid module requirement: {requirement!r}")
        match = _REQUIREMENT.fullmatch(requirement)
        if match is None:
            raise ValueError(f"Invalid exact module requirement: {requirement!r}")
        name = match.group("name")
        normalized = _normalize_name(name)
        if normalized in parsed:
            raise ValueError(f"Duplicate module requirement: {requirement!r}")
        parsed[normalized] = match.group("version")

    expected_external = {
        _normalize_name(spec.package)
        for skill_name, spec in SKILL_API_SPECS.items()
        if skill_name != "opera"
    }
    if set(parsed) != expected_external:
        missing = sorted(expected_external - set(parsed))
        unexpected = sorted(set(parsed) - expected_external)
        detail = []
        if missing:
            detail.append(f"missing: {', '.join(missing)}")
        if unexpected:
            detail.append(f"unexpected: {', '.join(unexpected)}")
        raise ValueError(
            "Module requirements do not match the API manifest ("
            + "; ".join(detail)
            + ")"
        )

    result = {_normalize_name(project_name): project_version}
    result.update(parsed)
    return result


def validate_installed_versions(expected: Mapping[str, str]) -> None:
    """Raise once with every missing or mismatched installed distribution."""
    problems: list[str] = []
    for package, expected_version in expected.items():
        try:
            installed_version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            problems.append(f"{package}: expected {expected_version}, not installed")
            continue
        if installed_version != expected_version:
            problems.append(
                f"{package}: expected {expected_version}, installed {installed_version}"
            )
    if problems:
        raise RuntimeError(
            "Installed distribution versions do not match:\n" + "\n".join(problems)
        )


def _validated_exports(module_name: str, module: object) -> list[str]:
    try:
        exports = getattr(module, "__all__")  # noqa: B009
    except AttributeError as exc:
        raise ValueError(f"Configured module {module_name!r} has no __all__") from exc
    if not isinstance(exports, (list, tuple)) or any(
        not isinstance(name, str) for name in exports
    ):
        raise ValueError(f"Configured module {module_name!r} has an invalid __all__")
    if len(set(exports)) != len(exports):
        raise ValueError(
            f"Configured module {module_name!r} has duplicate __all__ entries"
        )
    return sorted(exports)


def collect_api(spec: SkillApiSpec) -> dict[str, object]:
    """Collect the exact generated API contract for one skill."""
    exports: dict[str, list[str]] = {}
    signatures: dict[str, str] = {}
    for module_name in sorted(spec.modules):
        module = importlib.import_module(module_name)
        module_exports = _validated_exports(module_name, module)
        exports[module_name] = module_exports
        for export_name in module_exports:
            try:
                exported = getattr(module, export_name)
            except AttributeError as exc:
                raise ValueError(
                    f"Configured export {module_name}.{export_name} is missing"
                ) from exc
            if callable(exported):
                try:
                    signatures[f"{module_name}.{export_name}"] = str(
                        inspect.signature(exported)
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Cannot inspect callable {module_name}.{export_name}"
                    ) from exc
    return {
        "exports": exports,
        "package": spec.package,
        "signatures": dict(sorted(signatures.items())),
        "version": importlib.metadata.version(spec.package),
    }


def render_api_block(api: Mapping[str, object]) -> str:
    """Render one deterministic generated API region."""
    payload = json.dumps(dict(api), indent=2, sort_keys=True)
    return f"{_BEGIN_MARKER}\n## API\n\n```json\n{payload}\n```\n{_END_MARKER}"


def _front_matter_bounds(text: str) -> tuple[list[str], int]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError("Skill text must start with YAML front matter")
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            return lines, index
    raise ValueError("Skill text is missing its closing front matter delimiter")


def update_skill_text(text: str, spec: SkillApiSpec, api: Mapping[str, object]) -> str:
    """Update generated front matter and API text while preserving other prose."""
    lines, front_matter_end = _front_matter_bounds(text)
    field_lines: dict[str, list[int]] = {"module-package": [], "module-version": []}
    for index, line in enumerate(lines[1:front_matter_end], start=1):
        key, separator, _value = line.partition(":")
        if separator and key.strip() in field_lines:
            field_lines[key.strip()].append(index)
    for field, matches in field_lines.items():
        if len(matches) > 1:
            raise ValueError(f"Skill front matter has duplicate {field} fields")

    line_ending = "\n"
    if front_matter_end > 0 and lines[front_matter_end - 1].endswith("\r\n"):
        line_ending = "\r\n"
    package_line = f"module-package: {spec.package}{line_ending}"
    version_line = f'module-version: "{api["version"]}"{line_ending}'
    replacements = {"module-package": package_line, "module-version": version_line}
    for field, matches in field_lines.items():
        if matches:
            lines[matches[0]] = replacements[field]
        else:
            lines.insert(front_matter_end, replacements[field])
            front_matter_end += 1

    updated = "".join(lines)
    begin_count = updated.count(_BEGIN_MARKER)
    end_count = updated.count(_END_MARKER)
    if begin_count != 1 or end_count != 1:
        raise ValueError("Skill text must contain exactly one generated API region")
    begin = updated.index(_BEGIN_MARKER)
    end = updated.index(_END_MARKER, begin) + len(_END_MARKER)
    if (
        updated.find(_BEGIN_MARKER, end) != -1
        or updated.find(_END_MARKER, 0, begin) != -1
    ):
        raise ValueError("Skill text contains an unmatched generated API marker")
    return updated[:begin] + render_api_block(api) + updated[end:]


def sync_api_sections(
    skills_dir: Path = Path("src/opera/skills"),
    pyproject_path: Path = Path("pyproject.toml"),
) -> list[Path]:
    """Synchronize every skill, writing only after all files render."""
    if not skills_dir.is_dir() or not pyproject_path.is_file():
        raise FileNotFoundError(
            "Skill API synchronization requires src/opera/skills and pyproject.toml; "
            "run it from the repository root."
        )

    from opera.skills_manager import SKILL_FILES

    expected = load_expected_versions(pyproject_path)
    validate_installed_versions(expected)
    rendered: dict[Path, tuple[bytes, bytes]] = {}
    for skill_name, spec in SKILL_API_SPECS.items():
        path = skills_dir / SKILL_FILES[skill_name]
        old_bytes = path.read_bytes()
        old_text = old_bytes.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        api = collect_api(spec)
        new_text = update_skill_text(old_text, spec, api)
        new_bytes = new_text.encode("utf-8")
        rendered[path] = (old_bytes, new_bytes)

    changed = [path for path, (old, new) in rendered.items() if old != new]
    for path in changed:
        path.write_bytes(rendered[path][1])
    return changed
