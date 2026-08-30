from __future__ import annotations

import pytest

_MARKERS = (
    "contract: shared-schema and interface contract tests (fast)",
    "skill_snippet: isolated executable skill documentation snippets",
    "pipeline: cross-module end-to-end tests (slow)",
    "bvar: pipeline tests exercising the BVAR model",
    "midas: pipeline tests exercising the MIDAS-family models",
    "news: pipeline tests exercising the news/decomposition pipeline",
    "mixed_freq: pipeline tests exercising the real-time mixed-frequency pipeline",
    "ecosystem: pipeline tests exercising the full OPERA ecosystem illustration",
    "timeout: per-test timeout supplied by pytest-timeout",
)


def pytest_configure(config: pytest.Config) -> None:
    for marker in _MARKERS:
        config.addinivalue_line("markers", marker)
