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


def test_finding_rejects_bad_method():
    with pytest.raises(ValidationError):
        Finding(
            id="FD-003", finding_type=["Data_Fabrication"], title="t",
            description="d", severity="High", evidence_pack=[],
            detection_method="Not_A_Real_Method", confidence_score=0.5,
        )


def test_finding_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        Finding(
            id="FD-004", finding_type=["Data_Fabrication"], title="t",
            description="d", severity="High", evidence_pack=[],
            detection_method="GRIM", confidence_score=1.5,
        )


def test_finding_rejects_bad_severity():
    with pytest.raises(ValidationError):
        Finding(
            id="FD-005", finding_type=["Data_Fabrication"], title="t",
            description="d", severity="CRITICAL", evidence_pack=[],
            detection_method="GRIM", confidence_score=0.5,
        )


def test_finding_accepts_high_severity():
    f = Finding(
        id="FD-006", finding_type=["Data_Fabrication"], title="t",
        description="d", severity="High", evidence_pack=[],
        detection_method="GRIM", confidence_score=0.5,
    )
    assert f.severity == "High"
