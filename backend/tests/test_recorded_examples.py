"""Validate archived actual-run artifacts; these tests do not rerun Qwen or Docker."""
import hashlib
import json
from pathlib import Path

from nobluff.schemas import AnalysisReport

ROOT = Path(__file__).resolve().parents[2] / 'examples' / 'end-to-end'


def test_recorded_reports_have_valid_references_and_reproducible_test_bytes():
    for name in ('unicode','contradicted','inconclusive'):
        report = AnalysisReport.model_validate_json((ROOT/f'{name}-output.json').read_text())
        assert report.stage == 'complete'
        assert len(report.revision) == 40
        for test in report.approved_tests:
            assert test.test_hash == hashlib.sha256(test.test_code.encode()).hexdigest()
    unicode = AnalysisReport.model_validate_json((ROOT/'unicode-output.json').read_text())
    assert unicode.executions[0].status == 'failed'
    assert unicode.executions[1].status == 'passed'
    assert unicode.comparisons[0].status == 'fix_verified_for_test'
    source = AnalysisReport.model_validate_json((ROOT/'unicode-source-output.json').read_text())
    assert source.findings[0].assessment == 'inconclusive'
    assert source.executions == []
    assert json.loads((ROOT/'metadata.json').read_text())['synthetic_input'] is True
