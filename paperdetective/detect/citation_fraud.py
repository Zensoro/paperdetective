"""Citation fraud detection + retraction cross-check.

Network calls are injectable via the `_get` parameter so tests never hit
the wire; real usage degrades gracefully on network failure.
"""
from __future__ import annotations

import re
import urllib.request
from typing import Callable, Optional

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
RETRACTION_WORDS = ["retract", "correction", "erratum", "expression of concern"]


def validate_doi_format(doi: str) -> bool:
    return bool(DOI_RE.match(doi.strip()))


def _default_get(url: str, timeout: float = 5.0):
    req = urllib.request.Request(url, headers={"User-Agent": "PaperDetective/0.1"})
    return urllib.request.urlopen(req, timeout=timeout)


def check_doi_existence(doi: str, _get: Optional[Callable] = None) -> Optional[bool]:
    """Return True/False if resolvable, None if network unavailable."""
    if not validate_doi_format(doi):
        return False
    get = _get or _default_get
    try:
        resp = get(f"https://doi.org/{doi}", 5.0)
        status = getattr(resp, "status_code", getattr(resp, "status", 200))
        return status < 400
    except Exception:
        return None


def scan_retraction_keywords(meta: dict) -> list[str]:
    """Scan title/type for retraction signals."""
    text = f"{meta.get('title', '')} {meta.get('type', '')}".lower()
    return [w for w in RETRACTION_WORDS if w in text]
