"""Pro extension loading via entry points.

The open-source core is fully functional without any pro package. When the
user installs a pro extension (e.g. ``paperdetective-pro``), its entry points
under the ``paperdetective.pro`` group are discovered here and invoked by the
pipeline. Network/paid capabilities live *only* in the extension, never in
this repository, keeping the MIT core free and auditable.
"""
from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, List, Optional

from .schemas import Finding


class ProContext:
    """Handed to pro extensions so they can append findings without owning
    the report envelope. Keeps IDs unique via a local counter."""

    def __init__(self, start_id: int = 1, license_key: Optional[str] = None) -> None:
        self._next = start_id
        self.license_key = license_key
        self.findings: list[Finding] = []
        self.detectors_run: list[str] = []

    def add_finding(self, **kwargs) -> Finding:
        finding = Finding(id=f"FD-{self._next:03d}", **kwargs)
        self._next += 1
        self.findings.append(finding)
        return finding

    def mark_detector(self, name: str) -> None:
        if name not in self.detectors_run:
            self.detectors_run.append(name)


def load_pro_extensions() -> list[Any]:
    """Load all registered ``paperdetective.pro`` entry points.

    Returns [] when no pro package is installed (the default open-source
    install). Each extension must expose ``run_pro_detection(doc, ctx)``.
    """
    try:
        eps = entry_points(group="paperdetective.pro")
    except TypeError:  # Python < 3.10 uses the dict-returning API
        eps = entry_points().get("paperdetective.pro", [])
    return [ep.load() for ep in eps]
