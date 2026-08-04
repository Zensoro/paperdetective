"""Pro extension protocol tests: ProContext + entry-point loading."""
from paperdetective.plugins import ProContext, load_pro_extensions
from paperdetective.analyze import run_detection
from paperdetective.ingest import Document


def test_pro_context_unique_ids():
    ctx = ProContext(start_id=5)
    ctx.add_finding(finding_type=["Data_Fabrication"], title="a", description="d",
                    severity="High", evidence_pack=[], detection_method="GRIM",
                    confidence_score=0.9)
    ctx.add_finding(finding_type=["Data_Fabrication"], title="b", description="d",
                    severity="Low", evidence_pack=[], detection_method="GRIM",
                    confidence_score=0.5)
    assert [f.id for f in ctx.findings] == ["FD-005", "FD-006"]


def test_pro_context_mark_detector_dedup():
    ctx = ProContext()
    ctx.mark_detector("DOI_Check")
    ctx.mark_detector("DOI_Check")
    assert ctx.detectors_run == ["DOI_Check"]


def test_load_pro_extensions_returns_callables():
    # CI / 无 Pro 包环境返回 []；安装后返回可调用对象。此处不断言非空，
    # 只验证返回值类型稳定（list of callables or empty）。
    exts = load_pro_extensions()
    assert isinstance(exts, list)
    for e in exts:
        assert callable(e)


def test_run_detection_invokes_pro_extension(monkeypatch):
    class FakeExt:
        def __call__(self, doc, ctx):
            ctx.mark_detector("DOI_Check")
            ctx.add_finding(
                finding_type=["Citation_Fabrication"], title="fake DOI finding",
                description="DOI 无法解析", severity="High",
                evidence_pack=[], detection_method="DOI_Check",
                confidence_score=0.9,
            )
    monkeypatch.setattr("paperdetective.analyze.load_pro_extensions",
                        lambda: [FakeExt()])
    doc = Document(paper_id="p1", text="10.1016/j.fake.2023.01.001")
    result = run_detection([doc], pro=False)
    assert not result.detected_findings

    result = run_detection([doc], pro=True)
    assert any(f.detection_method == "DOI_Check" for f in result.detected_findings)
    assert "DOI_Check" in result.analysis_metadata["detectors_run"]
    # IDs stay unique alongside free findings
    ids = [f.id for f in result.detected_findings]
    assert len(ids) == len(set(ids))
