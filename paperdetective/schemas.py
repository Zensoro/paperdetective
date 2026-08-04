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
