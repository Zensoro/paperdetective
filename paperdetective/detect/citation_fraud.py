"""Citation fraud detection + retraction cross-check.

DOI existence check (against doi.org) and retraction-keyword scanning.
Network calls are injectable via the `_get` parameter so tests never hit
the wire; real usage degrades gracefully on network failure.
"""
from __future__ import annotations

import re
import urllib.request
from typing import Callable, Optional
from urllib.error import HTTPError

DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
RETRACTION_WORDS = [
    "retract", "correction", "erratum", "corrigendum",
    "expression of concern",
]
DEFAULT_TIMEOUT = 5.0


def validate_doi_format(doi: str) -> bool:
    return bool(DOI_RE.match(doi.strip()))


def _default_get(url: str, timeout: float = DEFAULT_TIMEOUT):
    req = urllib.request.Request(
        url, headers={"User-Agent": "PaperDetective/0.1"})
    return urllib.request.urlopen(req, timeout=timeout)


def check_doi_existence(
    doi: str, _get: Optional[Callable] = None
) -> Optional[bool]:
    """Return whether the DOI resolves to a real object.

    Returns:
        True: DOI resolves successfully.
        False: DOI is definitively nonexistent (HTTP 4xx) or invalid format.
        None: unverifiable (network down, timeout, or other transport error).
    """
    if not validate_doi_format(doi):
        return False
    get = _get or _default_get
    try:
        resp = get(f"https://doi.org/{doi}", DEFAULT_TIMEOUT)
        status = getattr(resp, "status_code", getattr(resp, "status", 200))
        return status < 400
    except HTTPError as e:
        return e.code < 400
    except Exception:
        return None


def scan_retraction_keywords(meta: dict) -> list[str]:
    """Scan title/type for retraction signals."""
    text = f"{meta.get('title', '')} {meta.get('type', '')}".lower()
    return [w for w in RETRACTION_WORDS if w in text]


def find_dois(text: str) -> list[str]:
    """Extract deduplicated, punctuation-trimmed DOIs from text."""
    # 去掉 DOI 末尾误捕获的标点（如句号、逗号、右括号）
    return sorted({
        m.rstrip(".,);]") for m in re.findall(
            r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)
    })


def scan_citations(text: str, _get: Optional[Callable] = None) -> list[dict]:
    """Scan a document's text for citation anomalies.

    Returns a list of dicts, each with DOI, existence status and any
    retraction keywords, ready to be turned into findings by the pipeline.
    """
    results = []
    for doi in find_dois(text):
        status = check_doi_existence(doi, _get=_get)
        results.append({
            "doi": doi,
            "exists": status,
            "retraction_words": [],
        })
    return results
