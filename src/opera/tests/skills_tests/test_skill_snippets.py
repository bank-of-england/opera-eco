from __future__ import annotations

import random
import re
from dataclasses import dataclass
from importlib import resources

import numpy as np
import pytest

from opera.skill_api import _BEGIN_MARKER, _END_MARKER
from opera.skills_manager import SKILL_FILES, SKILL_PACKAGE


@dataclass(frozen=True)
class SkillSnippet:
    skill_name: str
    filename: str
    index: int
    source: str
    skip_reason: str | None = None


_SKIP_DIRECTIVE = re.compile(r"^# skill-test: skip \(([^()\n]+)\)$")


def _parse_skip_directive(source: str, filename: str) -> str | None:
    lines = source.splitlines()
    nonblank_index = next(
        (index for index, line in enumerate(lines) if line.strip()), None
    )
    directives = [
        (index, line)
        for index, line in enumerate(lines)
        if line.startswith("# skill-test: skip")
    ]
    if not directives:
        return None
    first_index, first_line = directives[0]
    match = _SKIP_DIRECTIVE.fullmatch(first_line)
    if match is None:
        raise ValueError(f"{filename} has an invalid skill-test skip directive")
    if first_index != nonblank_index:
        raise ValueError(f"{filename} places its skip directive after executable code")
    if len(directives) > 1:
        raise ValueError(f"{filename} has multiple skill-test skip directives")
    return match.group(1)


def _extract_python_snippets(
    text: str, skill_name: str, filename: str
) -> list[SkillSnippet]:
    lines = text.splitlines()
    snippets: list[SkillSnippet] = []
    source_lines: list[str] | None = None
    index = 0
    for line in lines:
        if source_lines is None:
            if line.rstrip() == "```python":
                source_lines = []
                index += 1
        elif line.rstrip() == "```":
            source = "\n".join(source_lines)
            snippets.append(
                SkillSnippet(
                    skill_name,
                    filename,
                    index,
                    source,
                    _parse_skip_directive(source, filename),
                )
            )
            source_lines = None
        else:
            source_lines.append(line)
    if source_lines is not None:
        raise ValueError(f"{filename} has an unclosed Python fence")
    return snippets


def _skill_snippets(skill_name: str, filename: str) -> list[SkillSnippet]:
    source = resources.files(SKILL_PACKAGE).joinpath(filename)
    return _extract_python_snippets(
        source.read_text(encoding="utf-8"), skill_name, filename
    )


SNIPPETS = tuple(
    snippet
    for skill_name, filename in SKILL_FILES.items()
    for snippet in _skill_snippets(skill_name, filename)
)


@pytest.fixture(autouse=True)
def _isolate_skill_snippet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MPLBACKEND", "Agg")
    random.seed(0)
    np.random.seed(0)


@pytest.mark.contract
@pytest.mark.parametrize(
    "snippet",
    SNIPPETS,
    ids=[f"{snippet.skill_name} snippet {snippet.index}" for snippet in SNIPPETS],
)
def test_python_skill_snippet_compiles(snippet: SkillSnippet) -> None:
    compile(
        snippet.source,
        f"{snippet.filename}:snippet-{snippet.index}",
        "exec",
    )


@pytest.mark.skill_snippet
@pytest.mark.timeout(15)
@pytest.mark.parametrize(
    "snippet",
    tuple(snippet for snippet in SNIPPETS if snippet.skip_reason is None),
    ids=[
        f"{snippet.skill_name} snippet {snippet.index}"
        for snippet in SNIPPETS
        if snippet.skip_reason is None
    ],
)
def test_python_skill_snippet_executes(snippet: SkillSnippet) -> None:
    globals_dict = {"__name__": "__skill_test__"}
    exec(  # noqa: S102
        compile(snippet.source, f"{snippet.filename}:snippet-{snippet.index}", "exec"),
        globals_dict,
    )


@pytest.mark.contract
@pytest.mark.parametrize(
    ("skill_name", "filename"), tuple(SKILL_FILES.items()), ids=list(SKILL_FILES)
)
def test_every_canonical_skill_has_python_snippet(
    skill_name: str, filename: str
) -> None:
    assert _skill_snippets(skill_name, filename), f"{skill_name} has no Python snippet"


@pytest.mark.contract
def test_generated_markers_are_not_python_snippets() -> None:
    for filename in SKILL_FILES.values():
        text = (
            resources.files(SKILL_PACKAGE)
            .joinpath(filename)
            .read_text(encoding="utf-8")
        )
        assert text.count(_BEGIN_MARKER) == 1
        assert text.count(_END_MARKER) == 1


@pytest.mark.contract
def test_python_parser_rejects_unclosed_fence() -> None:
    with pytest.raises(ValueError, match="fake.md"):
        _extract_python_snippets("```python\nvalue = 1\n", "fake", "fake.md")


@pytest.mark.contract
def test_python_parser_requires_skip_reason_and_position() -> None:
    with pytest.raises(ValueError, match="invalid"):
        _extract_python_snippets(
            "```python\n# skill-test: skip\nvalue = 1\n```", "fake", "fake.md"
        )
    with pytest.raises(ValueError, match="after executable"):
        _extract_python_snippets(
            "```python\nvalue = 1\n# skill-test: skip (too late)\n```",
            "fake",
            "fake.md",
        )
