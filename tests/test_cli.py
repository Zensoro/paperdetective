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
    f.write_text("均值=1.333, n=2")
    out = tmp_path / "out.json"
    rc = main(["analyze", "--input", str(f), "--output", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["analysis_metadata"]["processing_status"] == "success"


def test_cli_accepts_directory_input(tmp_path):
    from paperdetective.cli import main
    d = tmp_path / "papers"
    d.mkdir()
    (d / "a.txt").write_text("均值=1.333, n=2")
    (d / "b.txt").write_text("普通论文")
    out = tmp_path / "out.json"
    rc = main(["analyze", "--input", str(d), "--output", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert len(data["analysis_metadata"]["papers"]) == 2


def test_cli_skips_unsupported_file_without_crashing(tmp_path):
    from paperdetective.cli import main
    good = tmp_path / "good.txt"
    good.write_text("普通论文")
    bad = tmp_path / "bad.xyz"
    bad.write_text("???")
    out = tmp_path / "out.json"
    rc = main(["analyze", "--input", str(good), str(bad), "--output", str(out)])
    assert rc == 0
    assert out.exists()


def test_cli_no_valid_input_returns_error(tmp_path):
    from paperdetective.cli import main
    rc = main(["analyze", "--input", str(tmp_path / "nonexistent_dir")])
    assert rc == 2


def test_cli_markdown_output(tmp_path):
    from paperdetective.cli import main
    f = tmp_path / "paper.txt"
    f.write_text("均值=1.333, n=2")
    out = tmp_path / "out.md"
    rc = main(["analyze", "--input", str(f), "--markdown", "--output", str(out)])
    assert rc == 0
    md = out.read_text()
    assert "PaperDetective 检测报告" in md
    assert "免责声明" in md
