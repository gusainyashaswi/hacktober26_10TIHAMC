"""Command errors must be actionable and must not write success artifacts."""

from nobluff.model import ExtractionError
from nobluff.model import __main__ as command


def test_missing_report_exits_cleanly(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv", ["extract", "--report", str(tmp_path / "missing.txt")]
    )
    assert command.main() == 2
    assert "Cannot read/write" in capsys.readouterr().err


def test_model_failure_does_not_write_output(tmp_path, monkeypatch, capsys):
    report = tmp_path / "input.txt"
    report.write_text("The exporter crashes.")
    output = tmp_path / "output.json"
    monkeypatch.setattr(
        "sys.argv", ["extract", "--report", str(report), "--output", str(output)]
    )

    def unavailable(text):
        raise ExtractionError("unavailable", "Start Ollama.")

    monkeypatch.setattr(command, "extract_claims", unavailable)
    assert command.main() == 2
    assert "unavailable: Start Ollama." in capsys.readouterr().err
    assert not output.exists()
