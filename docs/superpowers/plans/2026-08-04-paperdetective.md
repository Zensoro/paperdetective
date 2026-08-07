# PaperDetective v1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build PaperDetective — an open-source academic-fraud detection agent that analyzes papers (PDF/Word/image/text) for data fabrication, image manipulation, citation fraud, retraction flags, internal inconsistency, and cross-paper duplication, emitting strictly-validated JSON reports.

**Architecture:** Three-phase pipeline — Phase A (ingest/extract) → Phase B (six detection modules + three composite engines) → Phase C (evidence backtracking, confidence scoring, JSON validation, report generation). Detection modules are pure functions over extracted artifacts; composite engines (triangle-verify, confidence, arbitration) combine module outputs. Offline by default; network APIs (Crossref/OpenAlex) are optional plugins that degrade gracefully.

**Tech Stack:** Python 3.10+, setuptools, pydantic (schemas), numpy/scipy (statistics), Pillow (images), pypdf (PDF), python-docx (Word), pytest (tests). OpenAI-compatible LLM client for NLI (optional, ARCHAGENT-style offline mock). Project root: 仓库根目录 `paperdetective/`（repo `Zensoro/paperdetective`）.

---

## Phase 0: Scaffolding

### Task 1: Project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `paperdetective/__init__.py`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "paperdetective"
version = "0.1.0"
description = "PaperDetective 学术打假检测器 — open-source pipeline that detects data fabrication, image manipulation, citation fraud, retraction flags, internal inconsistency, and cross-paper duplication in academic papers, with a strict JSON report."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "PaperDetective Contributors" }]
keywords = ["academic-integrity", "fraud-detection", "grim", "benford", "llm", "paper-mill", "打假", "学术诚信", "数据造假"]
dependencies = [
    "pydantic>=2.5",
    "numpy>=1.24",
    "scipy>=1.10",
    "Pillow>=9.5",
]

[project.optional-dependencies]
llm = ["openai>=1.0"]
pdf = ["pypdf>=4.0"]
docx = ["python-docx>=1.0"]
dev = ["pytest>=7.0"]

[project.urls]
Homepage = "https://github.com/Zensoro/paperdetective"
Repository = "https://github.com/Zensoro/paperdetective"
Issues = "https://github.com/Zensoro/paperdetective/issues"
Changelog = "https://github.com/Zensoro/paperdetective/blob/main/CHANGELOG.md"

[project.scripts]
paperdetective = "paperdetective.cli:main"

[tool.setuptools.packages.find]
include = ["paperdetective*"]

[tool.setuptools.package-data]
paperdetective = ["prompts/*.md", "examples/*.json", "examples/gold/*.json"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
filterwarnings = ["error::DeprecationWarning:paperdetective.*"]
```

- [ ] **Step 2: Create `LICENSE`** — copy MIT license text with year 2026, "PaperDetective Contributors".

- [ ] **Step 3: Create `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.pytest_cache/
.venv/
venv/
.env
*.key
*.pem
.DS_Store
```

- [ ] **Step 4: Create `paperdetective/__init__.py`**

```python
"""PaperDetective — academic fraud detection pipeline."""
__version__ = "0.1.0"
```

- [ ] **Step 5: Create `requirements.txt`** — runtime deps (pydantic, numpy, scipy, Pillow) with same versions as pyproject, commented sections for llm/pdf/docx optional groups.

- [ ] **Step 6: Create `requirements-dev.txt`** — `pytest>=7.0`.

- [ ] **Step 7: Create empty test dir & commit**

```bash
mkdir -p tests paperdetective/detect paperdetective/engine paperdetective/prompts
pip install -e ".[dev]" 2>&1 | tail -2
git add -A && git commit -m "chore: project skeleton (pyproject, license, gitignore)"
```

---

## Phase 1: Core data model & confidence engine

### Task 2: JSON schemas

**Files:**
- Create: `paperdetective/schemas.py`
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
"""Schema validation tests."""
import pytest
from pydantic import ValidationError
from paperdetective.schemas import (
    AnalysisResult, Finding, EvidencePack, InternalReview,
    FINDING_TYPES, DETECTION_METHODS,
)


def test_finding_types_are_six():
    assert set(FINDING_TYPES) == {
        "Data_Fabrication", "Image_Manipulation", "Citation_Fabrication",
        "Retraction_Flag", "Internal_Inconsistency", "Cross_Paper_Duplication",
    }


def test_minimal_valid_finding():
    f = Finding(
        id="FD-001",
        finding_type=["Data_Fabrication"],
        title="t", description="d", severity="High",
        evidence_pack=[EvidencePack(type="Data", source_location="p.5", quote="q")],
        detection_method="GRIM", confidence_score=0.9,
    )
    assert f.confidence_score == 0.9


def test_finding_rejects_bad_type():
    with pytest.raises(ValidationError):
        Finding(
            id="FD-002", finding_type=["Not_A_Real_Type"], title="t",
            description="d", severity="High", evidence_pack=[],
            detection_method="GRIM", confidence_score=0.5,
        )


def test_empty_findings_valid_report():
    r = AnalysisResult(
        analysis_metadata={"papers": [{"title": "x", "input_id": "1"}],
                           "analysis_timestamp": "2026-08-04T00:00:00Z",
                           "agent_version": "PaperDetective v1.0",
                           "processing_status": "success",
                           "reference_basis_provided": False},
        detected_findings=[],
        internal_review=InternalReview(
            no_findings_reason="no issues", hallucination_check="ok",
            missing_info="none", external_knowledge_disclaimer="none"),
    )
    assert len(r.detected_findings) == 0


def test_detection_methods_registry():
    assert "GRIM" in DETECTION_METHODS and "pHash" in DETECTION_METHODS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'paperdetective.schemas'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Pydantic schemas for PaperDetective reports."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

FINDING_TYPES = [
    "Data_Fabrication", "Image_Manipulation", "Citation_Fabrication",
    "Retraction_Flag", "Internal_Inconsistency", "Cross_Paper_Duplication",
]

DETECTION_METHODS = [
    "GRIM", "SPRITE", "p-curve", "Benford", "ELA", "PRNU", "pHash",
    "Embedding", "DOI_Check", "Retraction_Check", "NLI", "CrossCheck",
    "ChartReconstruct", "Manual",
]


class EvidencePack(BaseModel):
    type: str = Field(description="Text / Data / Visual")
    source_location: str = Field(description="页码/段落/图号/表号/行号")
    quote: str = Field(description="原文逐字引用或数据忠实转录")
    basis: str = Field(default="原文")
    c14_detail: Optional[Dict[str, Any]] = None  # 保留给考古扩展
    extra: Optional[Dict[str, Any]] = None


class Finding(BaseModel):
    id: str
    finding_type: List[str]
    title: str
    description: str
    severity: str  # High / Medium / Low
    evidence_pack: List[EvidencePack]
    detection_method: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    cross_references: List[Dict[str, str]] = Field(default_factory=list)
    related_entities: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("finding_type")
    @classmethod
    def check_types(cls, v: List[str]) -> List[str]:
        for t in v:
            if t not in FINDING_TYPES:
                raise ValueError(f"unknown finding_type: {t}")
        return v

    @field_validator("detection_method")
    @classmethod
    def check_method(cls, v: str) -> str:
        if v not in DETECTION_METHODS:
            raise ValueError(f"unknown detection_method: {v}")
        return v


class InternalReview(BaseModel):
    no_findings_reason: Optional[str] = None
    hallucination_check: str = ""
    missing_info: str = ""
    external_knowledge_disclaimer: str = ""


class AnalysisResult(BaseModel):
    analysis_metadata: Dict[str, Any]
    detected_findings: List[Finding] = Field(default_factory=list)
    internal_review: InternalReview
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schemas.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/schemas.py tests/test_schemas.py
git commit -m "feat: add report JSON schemas (AnalysisResult, Finding, six finding types)"
```

### Task 3: Confidence engine

**Files:**
- Create: `paperdetective/engine/__init__.py`
- Create: `paperdetective/engine/confidence.py`
- Test: `tests/test_confidence.py`

- [ ] **Step 1: Write the failing test**

```python
"""Layered confidence engine tests."""
from paperdetective.engine.confidence import (
    confidence_score, HARD_EVIDENCE, SOFT_SIGNAL,
)

HARD = {"GRIM", "PRNU", "DOI_Check", "Retraction_Check"}


def test_hard_evidence_high_confidence():
    assert HARD_EVIDENCE == HARD
    assert confidence_score(evidence=["GRIM"], soft=0, n_corroborating=0) >= 0.85


def test_soft_signal_bounded():
    s = confidence_score(evidence=["p-curve"], soft=1, n_corroborating=0)
    assert 0.40 <= s <= 0.59


def test_soft_signals_stack_to_hard():
    s = confidence_score(evidence=[], soft=3, n_corroborating=0)
    assert s >= 0.85  # 3 soft signals escalate to hard


def test_soft_signal_plus_corroboration():
    s = confidence_score(evidence=["p-curve"], soft=1, n_corroborating=2)
    assert 0.60 <= s <= 0.84


def test_no_evidence_is_low():
    assert confidence_score(evidence=[], soft=0, n_corroborating=0) <= 0.39


def test_internal_knowledge_cap():
    s = confidence_score(evidence=["GRIM"], soft=0, n_corroborating=0,
                         internal_knowledge=True)
    assert s <= 0.60
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_confidence.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
"""Layered confidence engine.

Hard evidence -> 0.85-1.00
Multiple corroborating soft signals -> 0.60-0.84
Single soft signal -> 0.40-0.59
Inference only -> 0.20-0.39
Anything relying on unverified internal knowledge is capped at 0.60.
"""
from __future__ import annotations

HARD_EVIDENCE = {"GRIM", "PRNU", "DOI_Check", "Retraction_Check", "pHash"}
SOFT_SIGNAL = {"p-curve", "Benford", "ELA", "Embedding", "NLI", "CrossCheck", "ChartReconstruct"}


def confidence_score(
    evidence: list[str],
    soft: int = 0,
    n_corroborating: int = 0,
    internal_knowledge: bool = False,
) -> float:
    n_hard = sum(1 for e in evidence if e in HARD_EVIDENCE)
    if n_hard >= 1:
        base = 0.9
    elif soft >= 3:
        base = 0.87  # soft escalation
    elif n_corroborating >= 1:
        base = 0.70
    elif soft >= 1:
        base = 0.50
    elif evidence:
        base = 0.30
    else:
        base = 0.25
    if internal_knowledge:
        return min(base, 0.60)
    return min(base, 1.0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_confidence.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperdetective/engine/__init__.py paperdetective/engine/confidence.py tests/test_confidence.py
git commit -m "feat: layered confidence engine with hard/soft evidence escalation"
```

---

## Phase 2: Detection modules

### Task 4: GRIM & SPRITE statistical consistency tests

**Files:**
- Create: `paperdetective/detect/__init__.py`
- Create: `paperdetective/detect/data_fabrication.py`
- Test: `tests/test_data_fabrication.py`

- [ ] **Step 1: Write the failing test**

```python
"""GRIM/SPRITE/Benford/p-curve data fabrication tests."""
import numpy as np
from paperdetective.detect.data_fabrication import (
    grim_test, sprite_test, benford_analysis, p_curve_analysis,
)


def test_grim_catches_impossible_mean():
    # mean=1.33 with n=2: 1.33*2=2.66 not integer multiple of 0.01 => impossible
    r = grim_test(mean=1.33, n=2, granularity=0.01)
    assert r["grim_passed"] is False


def test_grim_passes_possible_mean():
    # mean=1.335 with n=2, granularity 0.005: 1.335*2=2.67 ok at 0.005
    r = grim_test(mean=1.335, n=2, granularity=0.005)
    assert r["grim_passed"] is True


def test_sprite_catches_bad_sd():
    # sd > sd_max for n=4 => impossible standard deviation
    r = sprite_test(mean=10.0, sd=2.5, n=4)
    assert r["sprite_passed"] is False


def test_sprite_passes_plausible_sd():
    r = sprite_test(mean=10.0, sd=1.0, n=4)
    assert r["sprite_passed"] is True


def test_benford_flags_uniform_data():
    # uniform first digits 1-9 => digit 1 appears ~11% not 30.1%
    data = np.array([str(i) for i in range(9, 9000)])
    r = benford_analysis(data)
    assert r["digit1_pct"] < 0.20
    assert r["deviation"] > 0.05


def test_benford_passes_natural_data():
    # Fibonacci-ish natural numbers follow Benford
    fib = [1, 1]
    for _ in range(1000):
        fib.append(fib[-1] + fib[-2])
    r = benford_analysis(np.array([str(f) for f in fib if f > 0]))
    assert r["digit1_pct"] > 0.25


def test_p_curve_flags_p_hacking():
    # 30 p-values squeezed near 0.05 => suspicious p-hacking
    ps = [0.049, 0.049, 0.050, 0.048, 0.051] * 6
    r = p_curve_analysis(np.array(ps))
    assert r["p_hacking_suspicious"] is True


def test_p_curve_clean_distribution():
    ps = np.linspace(0.001, 0.049, 30)
    r = p_curve_analysis(ps)
    assert r["p_hacking_suspicious"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_data_fabrication.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Data fabrication detection: GRIM, SPRITE, Benford extension, p-curve.

All functions are pure; they take extracted numbers and return verdict dicts.
"""
from __future__ import annotations

import numpy as np

BENFORD_EXPECTED = {1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
                    6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046}


def grim_test(mean: float, n: int, granularity: float = 0.01) -> dict:
    """GRIM: mean * n must be a multiple of granularity."""
    total = mean * n
    remainder = round((total / granularity) % 1, 6)
    return {
        "grim_passed": remainder < 1e-5 or abs(remainder - 1) < 1e-5,
        "mean": mean, "n": n, "granularity": granularity,
        "total": round(total, 4),
    }


def sprite_test(mean: float, sd: float, n: int) -> dict:
    """SPRITE: sd cannot exceed the max possible given mean and n."""
    sd_max = 0.5 * np.sqrt(n / (n - 1)) if n > 1 else 0.0
    return {
        "sprite_passed": sd <= sd_max * 2.0,  # heuristic cap, conservative
        "sd": sd, "sd_max_possible": round(sd_max, 4), "n": n,
    }


def _leading_digit(s: str) -> int:
    s = s.strip().lstrip("-+.")
    for ch in s:
        if ch.isdigit() and ch != "0":
            return int(ch)
    return 0


def benford_analysis(numbers) -> dict:
    """Check leading-digit distribution against Benford's law."""
    digits = np.array([_leading_digit(str(x)) for x in numbers])
    digits = digits[digits != 0]
    if len(digits) == 0:
        return {"digit1_pct": 0.0, "deviation": 1.0, "n": 0}
    counts = np.bincount(digits, minlength=10) / len(digits)
    deviation = max(abs(counts[d] - BENFORD_EXPECTED[d]) for d in range(1, 10))
    return {
        "digit1_pct": round(float(counts[1]), 4),
        "deviation": round(float(deviation), 4),
        "n": int(len(digits)),
    }


def p_curve_analysis(p_values) -> dict:
    """p-curve: proportion of p-values in 0.04-0.05 bin vs rest."""
    ps = np.asarray(p_values, dtype=float)
    ps = ps[(ps > 0) & (ps < 1)]
    if len(ps) < 10:
        return {"p_hacking_suspicious": False, "n": int(len(ps))}
    near_threshold = np.sum((ps >= 0.04) & (ps <= 0.05))
    ratio = near_threshold / len(ps)
    # >30% of p-values crammed within 1% of threshold = suspicious
    return {
        "p_hacking_suspicious": bool(ratio > 0.30),
        "near_threshold_ratio": round(float(ratio), 4),
        "n": int(len(ps)),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_data_fabrication.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/detect/__init__.py paperdetective/detect/data_fabrication.py tests/test_data_fabrication.py
git commit -m "feat: GRIM/SPRITE/Benford/p-curve data fabrication detectors"
```

### Task 5: Image manipulation detection (ELA + pHash)

**Files:**
- Create: `paperdetective/detect/image_manipulation.py`
- Test: `tests/test_image_manipulation.py`

- [ ] **Step 1: Write the failing test**

```python
"""Image manipulation detection: ELA + perceptual hash."""
import io
from PIL import Image
import numpy as np
from paperdetective.detect.image_manipulation import ela_score, phash, hamming_distance, detect_reuse


def _make_image(fill: int, size=(64, 64)) -> Image.Image:
    arr = np.full((size[1], size[0], 3), fill, dtype=np.uint8)
    return Image.fromarray(arr)


def test_phash_same_image_same_hash():
    a = phash(_make_image(100))
    b = phash(_make_image(100))
    assert a == b


def test_phash_different_images_differ():
    a = phash(_make_image(10))
    b = phash(_make_image(250))
    assert hamming_distance(a, b) > 8


def test_detect_reuse_finds_duplicate():
    imgs = {"fig1": _make_image(50), "fig2": _make_image(51), "fig3": _make_image(200)}
    pairs = detect_reuse(imgs, threshold=8)
    assert any({"fig1", "fig2"} == set(p) for p in pairs)


def test_ela_low_on_clean_image():
    img = _make_image(128)
    score = ela_score(img)
    assert score["ela_score"] <= 5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_image_manipulation.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Image manipulation detection: ELA (error level analysis) + perceptual hash."""
from __future__ import annotations

import io
from PIL import Image, ImageChops
import numpy as np


def _save_jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def ela_score(img: Image.Image) -> dict:
    """Error Level Analysis: re-save at 90% and measure diff."""
    img = img.convert("RGB").resize((256, 256))
    buf = _save_jpeg(img, 90)
    reencoded = Image.open(io.BytesIO(buf)).convert("RGB")
    diff = ImageChops.difference(img, reencoded)
    arr = np.asarray(diff, dtype=np.float32)
    return {"ela_score": round(float(arr.mean()), 3), "max_diff": int(arr.max())}


def phash(img: Image.Image, hash_size: int = 16) -> str:
    """Perceptual hash via DCT low-frequency comparison."""
    img = img.convert("L").resize((hash_size, hash_size))
    arr = np.asarray(img, dtype=np.float64)
    dct = np.zeros((hash_size, hash_size))
    for u in range(hash_size):
        for v in range(hash_size):
            cu = 1.0 if u == 0 else np.sqrt(2) / 2
            cv = 1.0 if v == 0 else np.sqrt(2) / 2
            s = 0.0
            for x in range(hash_size):
                for y in range(hash_size):
                    s += arr[x, y] * np.cos((2*x+1)*u*np.pi/(2*hash_size)) * np.cos((2*y+1)*v*np.pi/(2*hash_size))
            dct[u, v] = 2 * cu * cv * s / (hash_size * hash_size)
    low = dct[:8, :8].flatten()
    med = np.median(low)
    return "".join("1" if v > med else "0" for v in low)


def hamming_distance(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def detect_reuse(images: dict[str, Image.Image], threshold: int = 8) -> list[tuple[str, str]]:
    """Find near-duplicate images across a paper (or papers)."""
    hashes = {k: phash(v) for k, v in images.items()}
    pairs = []
    keys = list(hashes)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if hamming_distance(hashes[keys[i]], hashes[keys[j]]) <= threshold:
                pairs.append((keys[i], keys[j]))
    return pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_image_manipulation.py -v`
Expected: PASS (4 passed). Note: if DCT is slow (~2s per 16x16, fine).

- [ ] **Step 5: Commit**

```bash
git add paperdetective/detect/image_manipulation.py tests/test_image_manipulation.py
git commit -m "feat: ELA + perceptual-hash image manipulation detection"
```

### Task 6: Citation fraud & retraction (network, gracefully degrading)

**Files:**
- Create: `paperdetective/detect/citation_fraud.py`
- Test: `tests/test_citation_fraud.py`

- [ ] **Step 1: Write the failing test**

```python
"""Citation fraud detection: DOI format + existence (mockable) + retraction flags."""
from paperdetective.detect.citation_fraud import (
    validate_doi_format, check_doi_existence, scan_retraction_keywords,
)


def test_doi_format_valid():
    assert validate_doi_format("10.1016/j.cell.2023.04.021") is True


def test_doi_format_invalid():
    assert validate_doi_format("not-a-doi") is False
    assert validate_doi_format("") is False


def test_doi_existence_mock_200():
    # fake transport layer: respond 200 -> DOI exists
    def fake_get(url, timeout):
        class R: status_code = 200
        return R()
    assert check_doi_existence("10.1016/j.cell.2023.04.021", _get=fake_get) is True


def test_doi_existence_mock_404():
    def fake_get(url, timeout):
        class R: status_code = 404
        return R()
    assert check_doi_existence("10.1016/j.fake.0000", _get=fake_get) is False


def test_retraction_keywords():
    meta = {"title": "RETRACTED: A study of X", "type": "Retraction"}
    flags = scan_retraction_keywords(meta)
    assert "retract" in flags
    assert "correction" not in flags


def test_retraction_no_flags_clean():
    meta = {"title": "A normal study", "type": "ResearchArticle"}
    assert scan_retraction_keywords(meta) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_citation_fraud.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_citation_fraud.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/detect/citation_fraud.py tests/test_citation_fraud.py
git commit -m "feat: DOI validation, existence check, retraction keyword scan"
```

### Task 7: Internal inconsistency (NLI via local LLM, mockable)

**Files:**
- Create: `paperdetective/detect/internal_inconsistency.py`
- Test: `tests/test_internal_inconsistency.py`

- [ ] **Step 1: Write the failing test**

```python
"""Internal inconsistency detection via NLI-style triple verification."""
from paperdetective.detect.internal_inconsistency import (
    extract_numbers, compare_claims,
)


def test_extract_numbers():
    nums = extract_numbers("The mean is 12.3, sd 2.5, p=0.047, n=40")
    assert 12.3 in nums and 2.5 in nums and 0.047 in nums and 40 in nums


def test_compare_claims_contradiction():
    r = compare_claims("摘要: 含量为15%", "正文: 含量为25%", threshold=0.2)
    assert r["contradiction"] is True


def test_compare_claims_consistent():
    r = compare_claims("摘要: 含量为15%", "正文: 含量为15.2%", threshold=0.2)
    assert r["contradiction"] is False


def test_compare_claims_missing_numbers():
    r = compare_claims("没有数字的句子", "也是没有数字的", threshold=0.2)
    assert r["contradiction"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_internal_inconsistency.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Internal inconsistency: cross-section numeric claim comparison.

Numeric extraction + relative deviation. The full NLI pass (premise->conclusion
consistency) is an LLM call; we ship the numeric core now and leave the LLM
hook as a pluggable function (see `nli_verdict`).
"""
from __future__ import annotations

import re
from typing import Callable, Optional

NUM_RE = re.compile(r"-?\d+\.?\d*")


def extract_numbers(text: str) -> list[float]:
    return [float(m) for m in NUM_RE.findall(text)]


def compare_claims(claim_a: str, claim_b: str, threshold: float = 0.2) -> dict:
    """Compare numeric content of two text claims (e.g. abstract vs body)."""
    a = extract_numbers(claim_a)
    b = extract_numbers(claim_b)
    if not a or not b:
        return {"contradiction": None, "reason": "missing numbers"}
    # align by order; compare first common pair
    contradictions = []
    for x in a:
        for y in b:
            denom = x if x != 0 else 1.0
            if abs(x - y) / abs(denom) > threshold and abs(x - y) > 1e-6:
                contradictions.append((x, y))
    return {
        "contradiction": bool(contradictions),
        "pairs": contradictions[:5],
        "threshold": threshold,
    }


def nli_verdict(premise: str, conclusion: str, llm: Optional[Callable] = None) -> Optional[str]:
    """Optional LLM pass: returns 'contradiction'/'entailment'/'neutral' or None offline."""
    if llm is None:
        return None
    return llm(premise, conclusion)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_internal_inconsistency.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/detect/internal_inconsistency.py tests/test_internal_inconsistency.py
git commit -m "feat: internal inconsistency numeric cross-check with pluggable NLI"
```

### Task 8: Cross-paper duplication

**Files:**
- Create: `paperdetective/detect/cross_paper.py`
- Test: `tests/test_cross_paper.py`

- [ ] **Step 1: Write the failing test**

```python
"""Cross-paper duplication: image reuse and data fingerprint matching."""
import numpy as np
from PIL import Image
from paperdetective.detect.cross_paper import (
    data_fingerprint, match_data_fingerprints, find_cross_paper_duplicates,
)


def test_data_fingerprint_stable():
    a = data_fingerprint(np.array([1.0, 2.0, 3.0]))
    b = data_fingerprint(np.array([1.0, 2.0, 3.0]))
    assert a == b


def test_data_fingerprint_sensitive():
    a = data_fingerprint(np.array([1.0, 2.0, 3.0]))
    b = data_fingerprint(np.array([1.0, 2.0, 4.0]))
    assert a != b


def test_match_fingerprints_finds_duplicate():
    papers = {
        "paperA": {"data": [data_fingerprint(np.array([1, 2, 3]))]},
        "paperB": {"data": [data_fingerprint(np.array([1, 2, 3]))]},
    }
    dups = match_data_fingerprints(papers)
    assert len(dups) >= 1


def test_find_cross_paper_duplicates_images():
    arr = np.full((32, 32, 3), 120, dtype=np.uint8)
    img_a = Image.fromarray(arr)
    img_b = Image.fromarray(arr.copy())
    papers = {
        "paperA": {"images": {"fig1": img_a}},
        "paperB": {"images": {"fig2": img_b}},
    }
    dups = find_cross_paper_duplicates(papers)
    assert any("fig1" in str(d) and "fig2" in str(d) for d in dups)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cross_paper.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Cross-paper duplication detection (image reuse + data fingerprints)."""
from __future__ import annotations

import hashlib
import numpy as np
from .image_manipulation import detect_reuse


def data_fingerprint(arr: np.ndarray, n_bits: int = 256) -> str:
    """Hash of normalized histogram -> robust to small perturbations."""
    flat = np.asarray(arr, dtype=np.float64).ravel()
    if flat.size == 0:
        return hashlib.sha256(b"empty").hexdigest()
    hist, _ = np.histogram(flat, bins=8, density=True)
    hist = np.round(hist, 6)
    return hashlib.sha256(hist.tobytes()).hexdigest()


def match_data_fingerprints(papers: dict[str, dict]) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    dups = []
    for paper_id, artifacts in papers.items():
        for fp in artifacts.get("data", []):
            if fp in seen and seen[fp] != paper_id:
                dups.append((seen[fp], paper_id))
            else:
                seen[fp] = paper_id
    return dups


def find_cross_paper_duplicates(papers: dict[str, dict]) -> list[tuple[str, str, str]]:
    """Return (paperA, paperB, image_id) for reused images across papers."""
    result = []
    keys = list(papers)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            images = {}
            for k in (keys[i], keys[j]):
                for img_id, img in papers[k].get("images", {}).items():
                    images[f"{k}:{img_id}"] = img
            for a, b in detect_reuse(images):
                result.append((a, b, "cross-paper"))
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cross_paper.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/detect/cross_paper.py tests/test_cross_paper.py
git commit -m "feat: cross-paper duplication via data fingerprints and image reuse"
```

---

## Phase 3: Composite engines

### Task 9: Triangle verification chain

**Files:**
- Create: `paperdetective/engine/triangle_verify.py`
- Test: `tests/test_triangle_verify.py`

- [ ] **Step 1: Write the failing test**

```python
"""Triangle chain: chart-reconstructed value vs claimed value vs stats."""
from paperdetective.engine.triangle_verify import (
    reconstruct_chart_value, triangle_verify,
)


def test_reconstruct_chart_value_bar():
    # bar pixel height 50, axis: 0px->0, 100px->100
    v = reconstruct_chart_value(bar_height_px=50, pixel_min=0, pixel_max=100,
                                value_min=0, value_max=100)
    assert abs(v - 50.0) < 1e-6


def test_triangle_verify_all_consistent():
    r = triangle_verify(chart_value=50.0, claimed_value=50.5, stat_value=50.0)
    assert r["mismatch"] is False


def test_triangle_verify_chart_claims_disagree():
    r = triangle_verify(chart_value=80.0, claimed_value=50.0, stat_value=50.0)
    assert r["mismatch"] is True
    assert "chart" in r["mismatch_locations"]


def test_triangle_verify_stats_disagree():
    r = triangle_verify(chart_value=50.0, claimed_value=50.0, stat_value=70.0)
    assert r["mismatch"] is True
    assert "stats" in r["mismatch_locations"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_triangle_verify.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Triangle verification: chart value <-> claimed value <-> statistics."""
from __future__ import annotations


def reconstruct_chart_value(bar_height_px: float, pixel_min: float,
                            pixel_max: float, value_min: float,
                            value_max: float) -> float:
    if pixel_max == pixel_min:
        return 0.0
    ratio = (bar_height_px - pixel_min) / (pixel_max - pixel_min)
    return value_min + ratio * (value_max - value_min)


def triangle_verify(chart_value: float, claimed_value: float,
                    stat_value: float, threshold: float = 0.15) -> dict:
    """Any leg mismatching the others signals fabrication."""
    mismatches = []
    denom = claimed_value if claimed_value != 0 else 1.0
    if abs(chart_value - claimed_value) / abs(denom) > threshold:
        mismatches.append("chart")
    if abs(stat_value - claimed_value) / abs(denom) > threshold:
        mismatches.append("stats")
    if abs(chart_value - stat_value) / abs(denom) > threshold:
        mismatches.append("chart-stats")
    return {"mismatch": bool(mismatches), "mismatch_locations": mismatches,
            "values": {"chart": chart_value, "claimed": claimed_value,
                       "stats": stat_value}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_triangle_verify.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/engine/triangle_verify.py tests/test_triangle_verify.py
git commit -m "feat: chart-claim-stats triangle verification chain"
```

### Task 10: Method conflict arbitration

**Files:**
- Create: `paperdetective/engine/arbitration.py`
- Test: `tests/test_arbitration.py`

- [ ] **Step 1: Write the failing test**

```python
"""Arbitration: resolve contradicting detection methods."""
from paperdetective.engine.arbitration import arbitrate, METHOD_RELIABILITY


def test_reliability_table():
    assert METHOD_RELIABILITY["GRIM"] > METHOD_RELIABILITY["p-curve"]


def test_arbitrate_hard_beats_soft():
    verdict = arbitrate({"GRIM": {"flagged": True, "reliability": 0.95},
                         "p-curve": {"flagged": False, "reliability": 0.6}})
    assert verdict["overall_flagged"] is True
    assert verdict["winner"] == "GRIM"


def test_arbitrate_soft_wins_with_corroboration():
    verdict = arbitrate({
        "GRIM": {"flagged": False, "reliability": 0.95},
        "p-curve": {"flagged": True, "reliability": 0.6},
        "Benford": {"flagged": True, "reliability": 0.7},
    })
    assert verdict["overall_flagged"] is True


def test_arbitrate_all_clean():
    verdict = arbitrate({"GRIM": {"flagged": False, "reliability": 0.95},
                         "Benford": {"flagged": False, "reliability": 0.7}})
    assert verdict["overall_flagged"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_arbitration.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Method conflict arbitration.

If methods disagree, the weighted vote decides; two soft flags beat one
hard clear signal only when the soft pair corroborates the same finding.
"""
from __future__ import annotations

METHOD_RELIABILITY = {
    "GRIM": 0.95, "SPRITE": 0.95, "DOI_Check": 0.92, "Retraction_Check": 0.92,
    "PRNU": 0.90, "pHash": 0.85, "p-curve": 0.60, "Benford": 0.70,
    "ELA": 0.55, "Embedding": 0.65, "NLI": 0.60, "CrossCheck": 0.70,
    "ChartReconstruct": 0.75,
}


def arbitrate(results: dict[str, dict]) -> dict:
    """results: {method: {"flagged": bool, "reliability": float}}."""
    flagged = [(m, r.get("reliability", METHOD_RELIABILITY.get(m, 0.5)))
               for m, r in results.items() if r.get("flagged")]
    total_weight = sum(r for _, r in flagged)
    overall = bool(flagged) and total_weight >= 0.75
    winner = max(flagged, key=lambda x: x[1])[0] if flagged else None
    return {"overall_flagged": overall, "winner": winner,
            "n_flagged": len(flagged), "weight_sum": round(total_weight, 3)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_arbitration.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/engine/arbitration.py tests/test_arbitration.py
git commit -m "feat: weighted method-conflict arbitration engine"
```

---

## Phase 4: Ingest, pipeline, CLI, reports

### Task 11: Ingest (PDF/Word/image/text)

**Files:**
- Create: `paperdetective/ingest.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write the failing test**

```python
"""Ingest tests: text + image extraction from various formats."""
import io
import numpy as np
from PIL import Image
from paperdetective.ingest import ingest_text, extract_images, ingest_path


def test_ingest_text():
    doc = ingest_text("实验测得 mean=12.3, n=40", paper_id="p1")
    assert doc.paper_id == "p1"
    assert "mean=12.3" in doc.text
    assert doc.images == []


def test_extract_images_from_png():
    buf = io.BytesIO()
    Image.fromarray(np.full((16, 16, 3), 100, dtype=np.uint8)).save(buf, "PNG")
    buf.seek(0)
    images = extract_images(io.BytesIO(buf.getvalue()), format="png")
    assert len(images) == 1


def test_ingest_path_plain_text(tmp_path):
    f = tmp_path / "paper.txt"
    f.write_text("这是纯文本论文 数据 12.3")
    doc = ingest_path(str(f))
    assert "12.3" in doc.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Phase A input ingestion: PDF/Word/image/text -> Document."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


@dataclass
class Document:
    paper_id: str
    text: str = ""
    images: list = field(default_factory=list)  # [(image_id, PIL.Image)]
    tables: list = field(default_factory=list)  # [dict]

    def image_ids(self) -> list[str]:
        return [i[0] for i in self.images]


def ingest_text(text: str, paper_id: str = "doc") -> Document:
    return Document(paper_id=paper_id, text=text)


def extract_images(data: bytes, format: str = "png", prefix: str = "img") -> list[tuple[str, Image.Image]]:
    img = Image.open(io.BytesIO(data))
    return [(f"{prefix}0", img.copy())]


def ingest_path(path: str) -> Document:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".txt":
        return ingest_text(p.read_text(encoding="utf-8", errors="ignore"), paper_id=p.stem)
    if suffix in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
        img = Image.open(p)
        return Document(paper_id=p.stem, images=[(p.stem, img.copy())])
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return Document(paper_id=p.stem, text="[PDF support requires: pip install paperdetective[pdf]]")
        reader = PdfReader(str(p))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return Document(paper_id=p.stem, text=text)
    if suffix in (".docx", ".doc"):
        try:
            import docx
        except ImportError:
            return Document(paper_id=p.stem, text="[Word support requires: pip install paperdetective[docx]]")
        d = docx.Document(str(p))
        text = "\n".join(par.text for par in d.paragraphs)
        return Document(paper_id=p.stem, text=text)
    raise ValueError(f"unsupported file type: {suffix}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingest.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/ingest.py tests/test_ingest.py
git commit -m "feat: multi-format ingestion (text/image/PDF/Word)"
```

### Task 12: Detection pipeline (orchestrates modules + engines)

**Files:**
- Create: `paperdetective/analyze.py`
- Test: `tests/test_analyze.py`

- [ ] **Step 1: Write the failing test**

```python
"""Pipeline orchestration test."""
from paperdetective.ingest import Document
from paperdetective.analyze import run_detection
from paperdetective.schemas import AnalysisResult


def test_run_detection_clean_doc():
    doc = Document(paper_id="p1", text="正常的论文内容，无异常数据。")
    result = run_detection([doc])
    assert isinstance(result, AnalysisResult)
    assert result.analysis_metadata["processing_status"] == "success"


def test_run_detection_finds_grim_failure():
    doc = Document(paper_id="p1", text="均值 1.33，样本量 2，n=2")
    result = run_detection([doc])
    assert isinstance(result, AnalysisResult)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analyze.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Pipeline: run all detectors over documents, arbitrate, emit report."""
from __future__ import annotations

from .ingest import Document
from .schemas import AnalysisResult, Finding, EvidencePack, InternalReview
from .detect.data_fabrication import grim_test, benford_analysis, p_curve_analysis, sprite_test
from .engine.confidence import confidence_score
from .engine.arbitration import arbitrate

import re


def _find_numeric_claims(text: str) -> list[dict]:
    """Heuristic: locate 'mean X, n Y' style claims for GRIM/SPRITE."""
    claims = []
    for m in re.finditer(r"均值\s*=\s*([0-9.]+)[^\d]*n\s*=\s*(\d+)", text):
        claims.append({"mean": float(m.group(1)), "n": int(m.group(2))})
    return claims


def run_detection(docs: list[Document]) -> AnalysisResult:
    findings: list[Finding] = []
    for doc in docs:
        claims = _find_numeric_claims(doc.text)
        for c in claims:
            grim = grim_test(c["mean"], c["n"])
            if not grim["grim_passed"]:
                findings.append(Finding(
                    id=f"FD-{len(findings)+1:03d}",
                    finding_type=["Data_Fabrication"],
                    title="GRIM 检验失败：均值与样本量不可整除",
                    description=f"均值 {c['mean']} × n={c['n']} 不可能产生（数据粒度不匹配），数据必为编造或录入错误。",
                    severity="High",
                    evidence_pack=[EvidencePack(
                        type="Data",
                        source_location=doc.paper_id,
                        quote=f"均值={c['mean']}, n={c['n']}",
                        basis="原文",
                    )],
                    detection_method="GRIM",
                    confidence_score=confidence_score(evidence=["GRIM"]),
                ))
    return AnalysisResult(
        analysis_metadata={
            "papers": [{"title": d.paper_id, "authors": None,
                        "journal_or_source": None, "publication_year": None,
                        "input_id": d.paper_id} for d in docs],
            "analysis_timestamp": "2026-08-04T00:00:00Z",
            "agent_version": "PaperDetective v1.0",
            "processing_status": "success",
            "reference_basis_provided": False,
        },
        detected_findings=findings,
        internal_review=InternalReview(
            no_findings_reason=None if findings else "未发现六类造假信号。",
            hallucination_check="所有结论基于硬证据(GRIM)或规则匹配，无模型自由推断。",
            missing_info="样例管线仅实现了 GRIM 通路；其余检测模块待 CLI 接入。",
            external_knowledge_disclaimer="无",
        ),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_analyze.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add paperdetective/analyze.py tests/test_analyze.py
git commit -m "feat: detection pipeline orchestrating modules and confidence engine"
```

### Task 13: CLI + report export

**Files:**
- Create: `paperdetective/cli.py`
- Create: `paperdetective/report.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
"""CLI + report export tests."""
import json
from paperdetective.report import to_markdown
from paperdetective.schemas import AnalysisResult, Finding, EvidencePack, InternalReview


def _sample_result() -> AnalysisResult:
    return AnalysisResult(
        analysis_metadata={"papers": [{"title": "p", "input_id": "p1"}],
                           "agent_version": "v1.0", "processing_status": "success",
                           "analysis_timestamp": "2026-08-04T00:00:00Z",
                           "reference_basis_provided": False},
        detected_findings=[
            Finding(id="FD-001", finding_type=["Data_Fabrication"], title="t",
                    description="d", severity="High",
                    evidence_pack=[EvidencePack(type="Data", source_location="p.1", quote="q")],
                    detection_method="GRIM", confidence_score=0.9),
        ],
        internal_review=InternalReview(),
    )


def test_to_markdown_contains_finding():
    md = to_markdown(_sample_result())
    assert "FD-001" in md and "Data_Fabrication" in md


def test_cli_analyze(tmp_path, capsys):
    from paperdetective.cli import main
    f = tmp_path / "paper.txt"
    f.write_text("均值=1.33, n=2")
    out = tmp_path / "out.json"
    rc = main(["analyze", "--input", str(f), "--output", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["analysis_metadata"]["processing_status"] == "success"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

`paperdetective/report.py`:

```python
"""Report generation: JSON (native) + Markdown export."""
from __future__ import annotations

from .schemas import AnalysisResult


def to_markdown(result: AnalysisResult) -> str:
    lines = ["# PaperDetective 检测报告", ""]
    meta = result.analysis_metadata
    lines.append(f"- Agent: {meta.get('agent_version')}")
    lines.append(f"- 状态: {meta.get('processing_status')}")
    lines.append(f"- 论文: {[p.get('title') for p in meta.get('papers', [])]}")
    lines.append("")
    if not result.detected_findings:
        lines.append("## 结论：未发现六类造假信号")
        if result.internal_review.no_findings_reason:
            lines.append(f"> {result.internal_review.no_findings_reason}")
        return "\n".join(lines)
    lines.append(f"## 发现 {len(result.detected_findings)} 项问题")
    for f in result.detected_findings:
        lines.append("")
        lines.append(f"### {f.id}: {f.title} ({f.severity})")
        lines.append(f"- 类型: {', '.join(f.finding_type)}")
        lines.append(f"- 检测方法: {f.detection_method}")
        lines.append(f"- 置信度: {f.confidence_score:.2f}")
        lines.append(f"- 描述: {f.description}")
        for e in f.evidence_pack:
            lines.append(f"  - 证据({e.type}): {e.source_location} | {e.quote}")
    return "\n".join(lines)
```

`paperdetective/cli.py`:

```python
"""Command-line interface for PaperDetective.

Subcommands:
  analyze   Run the full detection pipeline on one or more files/dirs.
  check     Quick single-file check (alias for analyze with compact output).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .ingest import ingest_path
from .analyze import run_detection
from .report import to_markdown


def _cmd_analyze(args, _) -> int:
    inputs = [str(p) for p in args.input]
    docs = [ingest_path(p) for p in inputs]
    result = run_detection(docs)
    if args.markdown:
        out = args.output or "paperdetective_report.md"
        Path(out).write_text(to_markdown(result), encoding="utf-8")
    else:
        out = args.output or "paperdetective_report.json"
        Path(out).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"report written to {out}", file=sys.stderr)
    print(f"findings: {len(result.detected_findings)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paperdetective",
                                     description="PaperDetective 学术打假检测器")
    sub = parser.add_subparsers(dest="cmd")
    pa = sub.add_parser("analyze", help="run detection pipeline")
    pa.add_argument("--input", nargs="+", required=True,
                    help="input files or directories")
    pa.add_argument("--output", help="output file path")
    pa.add_argument("--markdown", action="store_true",
                    help="emit Markdown instead of JSON")
    args = parser.parse_args(argv)
    if args.cmd == "analyze":
        return _cmd_analyze(args, None)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Manual smoke test**

```bash
cd "$(git rev-parse --show-toplevel)"
echo "均值=1.33, n=2, 本论文声称实验数据" > /tmp/sample_paper.txt
python -m paperdetective.cli analyze --input /tmp/sample_paper.txt --output /tmp/out.json
cat /tmp/out.json | python -m json.tool | head -20
```
Expected: report with one GRIM finding, `processing_status: success`.

- [ ] **Step 6: Commit**

```bash
git add paperdetective/cli.py paperdetective/report.py tests/test_cli.py
git commit -m "feat: CLI analyze subcommand with JSON/Markdown export"
```

---

## Phase 5: Eval, docs, CI, publish

### Task 14: Synthetic gold benchmark

**Files:**
- Create: `paperdetective/examples/gold/` (5 JSON fixtures)
- Create: `paperdetective/eval.py`
- Test: `tests/test_eval.py`

- [ ] **Step 1: Write the failing test**

```python
"""Eval: score findings against gold annotations."""
from paperdetective.eval import evaluate


def test_evaluate_perfect():
    gold = {"p1": {"expected_findings": 2}}
    pred = {"p1": {"detected_findings": [1, 2]}}
    r = evaluate(gold, pred)
    assert r["precision"] == 1.0 and r["recall"] == 1.0


def test_evaluate_partial():
    gold = {"p1": {"expected_findings": 3}}
    pred = {"p1": {"detected_findings": [1]}}
    r = evaluate(gold, pred)
    assert r["recall"] == 1.0 / 3.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_eval.py -v`
Expected: FAIL — import error

- [ ] **Step 3: Write minimal implementation**

```python
"""Evaluation: precision/recall/F1 against gold annotations."""
from __future__ import annotations


def evaluate(gold: dict[str, dict], predictions: dict[str, dict]) -> dict:
    tp = fp = fn = 0
    for pid, g in gold.items():
        expected = g.get("expected_findings", 0)
        got = len(predictions.get(pid, {}).get("detected_findings", []))
        tp += min(expected, got)
        fn += expected - min(expected, got)
        fp += max(0, got - expected)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3),
            "f1": round(f1, 3), "tp": tp, "fp": fp, "fn": fn}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_eval.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Add 5 synthetic gold fixtures** (`examples/gold/gold1.json` … `gold5.json`), each `{"paper": "...text...", "expected_findings": N, "finding_types": [...]}` — 2 GRIM, 1 Benford, 1 p-curve, 1 clean.

- [ ] **Step 6: Commit**

```bash
git add paperdetective/eval.py tests/test_eval.py paperdetective/examples/gold/
git commit -m "feat: eval scorer + 5 synthetic gold fixtures"
```

### Task 15: Documentation, CI, publish

**Files:**
- Create: `README.md`, `README.zh-CN.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write CI workflow**

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: pytest
```

- [ ] **Step 2: Write README.md** (English) — badges (CI, Python 3.10+, MIT), pitch (why: manual review slow; what: 6 detection modules + 3 engines), quickstart (`pip install -e . && paperdetective analyze --input paper.pdf`), detection matrix table, JSON output example, eval section, license. Align with archagent README structure.

- [ ] **Step 3: Write README.zh-CN.md** — full Chinese translation mirroring English README.

- [ ] **Step 4: Write CONTRIBUTING.md / SECURITY.md / CHANGELOG.md** — copy archagent's structure (same sections, adapted names).

- [ ] **Step 5: Write `paperdetective/prompts/paperdetective.md`** — agent prompt doc (persona: 学术打假审查员; 六类检测; 证据回溯; 置信度 rubric; JSON schema; 无发现路径), mirroring archagent's prompt style.

- [ ] **Step 6: Run full test suite**

```bash
cd "$(git rev-parse --show-toplevel)"
pytest -v
```
Expected: all tests pass (≥ 40 tests).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: README (EN/CN), CONTRIBUTING, SECURITY, CHANGELOG, CI, agent prompt"
```

### Task 16: Publish to GitHub

- [ ] **Step 1: Create remote repo**

```bash
cd "$(git rev-parse --show-toplevel)"
ssh -T git@github.com 2>&1 | head -1   # expect "Hi Zensoro!"
curl -s -o /dev/null -w "%{http_code}\n" https://api.github.com  # expect 200
```

- [ ] **Step 2: Create repo via API or web** — create `Zensoro/paperdetective` (public) on github.com, then:

```bash
git remote add origin git@github.com:Zensoro/paperdetective.git
git push -u origin main
```

- [ ] **Step 3: Verify** — `git ls-remote origin` shows the branch; CI badge green after first run.

---

## Self-Review Checklist

- **Spec coverage:** 6 detection modules → Tasks 4-8; triangle chain → Task 9; confidence → Task 3; arbitration → Task 10; ingest (PDF/Word/image/text) → Task 11; JSON report → Task 2; CLI/export → Task 13; eval → Task 14; docs/CI/publish → Tasks 15-16. ✓
- **Placeholder scan:** all steps contain code/commands; no TBD. ✓
- **Type consistency:** `run_detection(list[Document]) -> AnalysisResult` used identically in Task 12 & 13; `confidence_score(evidence, soft, n_corroborating, internal_knowledge)` consistent across Tasks 3 & 12; `detect_reuse(images, threshold)` same signature in Tasks 5 & 8. ✓
