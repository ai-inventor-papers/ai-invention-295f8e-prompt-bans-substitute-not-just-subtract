"""Hash chain: verify() detects a 1-byte edit of a committed file (testing_plan 6)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_chain_detects_edit(tmp_path, monkeypatch):
    import cfg5
    import commit5
    log = tmp_path / "commitments.log"
    monkeypatch.setattr(cfg5, "COMMIT_LOG", log)
    monkeypatch.setattr(commit5, "COMMIT_LOG", log)
    monkeypatch.setattr(cfg5, "ROOT", tmp_path)
    monkeypatch.setattr(commit5, "ROOT", tmp_path)
    f = tmp_path / "a.json"
    f.write_text('{"x": 1}')
    commit5.commit([f], "T")
    assert commit5.verify()["files_changed_since_commit"] == 0
    f.write_text('{"x": 2}')
    assert commit5.verify()["files_changed_since_commit"] == 1
    lines = log.read_text().splitlines()
    parts = lines[0].split()
    parts[2] = "0" + parts[2][1:]
    log.write_text(" ".join(parts) + "\n")
    assert commit5.verify()["chain_breaks"] == 1
