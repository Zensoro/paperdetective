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


def test_run_detection_crash_safety_on_trailing_period():
    doc = Document(paper_id="p1", text="均值=1.333. n=2 以及 p=0.04. p=0.05")
    result = run_detection([doc])
    assert isinstance(result, AnalysisResult)


def test_run_detection_mode_metadata():
    doc = Document(paper_id="p1", text="普通论文")
    free_r = run_detection([doc], pro=False)
    pro_r = run_detection([doc], pro=True)
    assert free_r.analysis_metadata["mode"] == "free"
    assert pro_r.analysis_metadata["mode"] == "pro"


def test_run_detection_english_mean_claim():
    doc = Document(paper_id="p1", text="The treatment group (mean = 2.66, n = 2) improved.")
    result = run_detection([doc])
    assert any(f.detection_method == "GRIM" for f in result.detected_findings)


def test_run_detection_image_reuse_within_paper():
    import numpy as np
    from PIL import Image
    arr = np.full((32, 32, 3), 120, dtype=np.uint8)
    doc = Document(paper_id="p1", text="",
                   images=[("fig1", Image.fromarray(arr)),
                           ("fig2", Image.fromarray(arr.copy()))])
    result = run_detection([doc])
    assert any(f.detection_method == "pHash" and "Image_Manipulation" in f.finding_type
               for f in result.detected_findings)


def test_run_detection_cross_paper_reuse():
    import numpy as np
    from PIL import Image
    arr = np.full((32, 32, 3), 120, dtype=np.uint8)
    a = Document(paper_id="pA", text="", images=[("fig1", Image.fromarray(arr))])
    b = Document(paper_id="pB", text="", images=[("fig2", Image.fromarray(arr.copy()))])
    result = run_detection([a, b])
    assert any("Cross_Paper_Duplication" in f.finding_type
               for f in result.detected_findings)


def test_run_detection_benford_small_sample_no_false_positive():
    # 少量数字不触发 Benford（样本不足），避免误报
    doc = Document(paper_id="p1", text="均值=1.5, n=3, 结果见表 2，共 4 组。")
    result = run_detection([doc])
    assert not any(f.detection_method == "Benford" for f in result.detected_findings)


def test_run_detection_metadata_lists_detectors():
    doc = Document(paper_id="p1", text="均值=1.5, n=3")
    result = run_detection([doc])
    assert "GRIM" in result.analysis_metadata["detectors_run"]
