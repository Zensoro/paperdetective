"""Tests for evidence-figure export tool."""
import json
import os

from PIL import Image

from paperdetective.tools.export_evidence_fig import export


def _write_report(path, findings):
    json.dump({"detected_findings": findings}, open(path, "w"))


def test_export_writes_montage(tmp_path):
    fig = Image.new("RGB", (64, 48), "white")
    fig.save(tmp_path / "figA.png")
    fig.save(tmp_path / "figB.png")
    report = tmp_path / "r.json"
    _write_report(report, [{
        "id": "FD-001",
        "detection_method": "LaneReuse",
        "evidence_pack": [{
            "type": "Visual",
            "extra": {"figure_a": "figA", "figure_b": "figB",
                      "box_a": [0, 0, 16, 48], "box_b": [20, 0, 40, 48]},
        }],
    }])
    out = tmp_path / "ev"
    written = export(str(report), str(tmp_path), str(out))
    assert len(written) == 1
    assert os.path.exists(written[0])


def test_export_skips_non_lanereuse(tmp_path):
    report = tmp_path / "r.json"
    _write_report(report, [{"id": "FD-001", "detection_method": "GRIM",
                            "evidence_pack": []}])
    out = tmp_path / "ev"
    assert export(str(report), str(tmp_path), str(out)) == []


def test_export_skips_missing_box(tmp_path):
    report = tmp_path / "r.json"
    _write_report(report, [{"id": "FD-001", "detection_method": "LaneReuse",
                            "evidence_pack": [{"type": "Visual", "extra": {}}]}])
    out = tmp_path / "ev"
    assert export(str(report), str(tmp_path), str(out)) == []


def test_export_resolves_extension(tmp_path):
    fig = Image.new("RGB", (64, 48), "white")
    fig.save(tmp_path / "figA.png")
    fig.save(tmp_path / "figB.png")
    report = tmp_path / "r.json"
    _write_report(report, [{
        "id": "FD-001", "detection_method": "LaneReuse",
        "evidence_pack": [{
            "type": "Visual",
            "extra": {"figure_a": "figA", "figure_b": "figB",
                      "box_a": [0, 0, 16, 48], "box_b": [20, 0, 40, 48]},
        }],
    }])
    out = tmp_path / "ev"
    written = export(str(report), str(tmp_path), str(out))
    assert len(written) == 1
