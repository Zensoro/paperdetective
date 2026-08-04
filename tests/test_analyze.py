"""Pipeline orchestration test."""
from paperdetective.ingest import Document
from paperdetective.analyze import run_detection
from paperdetective.schemas import AnalysisResult


def test_run_detection_clean_doc():
    doc = Document(paper_id="p1", text="正常的论文内容，无异常数据。")
    result = run_detection([doc])
    assert isinstance(result, AnalysisResult)
    assert result.analysis_metadata["processing_status"] == "success"
    assert len(result.detected_findings) == 0


def test_run_detection_finds_grim_failure():
    doc = Document(paper_id="p1", text="均值=1.333，样本量 n=2，本论文声称数据可靠")
    result = run_detection([doc])
    assert isinstance(result, AnalysisResult)
    # 1.333*2 = 2.666 is NOT a multiple of 0.01 → GRIM violation
    assert any(f.detection_method == "GRIM" for f in result.detected_findings)


def test_run_detection_has_disclaimer():
    doc = Document(paper_id="p1", text="普通论文")
    result = run_detection([doc])
    assert "筛查信号" in result.internal_review.disclaimer


def test_run_detection_pro_mode_disables_network():
    # pro=False (default) should NOT call network DOI check
    doc = Document(paper_id="p1", text="10.1016/j.cell.2023.04.021 被引用")
    result = run_detection([doc], pro=False)
    assert isinstance(result, AnalysisResult)
