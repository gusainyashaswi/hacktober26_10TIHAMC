"""Portable exports of the same validated report returned by the API."""

from nobluff.schemas import AnalysisReport


def _block(text: str) -> str:
    # Any embedded run of backticks must be shorter than our fence.
    import re

    fence = "`" * max(3, max((len(x) for x in re.findall(r"`+", text)), default=0) + 1)
    return f"{fence}text\n{text}\n{fence}"


def export_report(report: AnalysisReport, format: str) -> str:
    report = AnalysisReport.model_validate(report.model_dump())
    if format == "json":
        return report.model_dump_json(indent=2) + "\n"
    if format != "markdown":
        raise ValueError("Supported formats: json, markdown")
    lines = [
        "# NoBluff investigation report",
        "",
        f"Stage: {report.stage}",
        "",
        "This report contains model interpretations; inspect evidence and limitations.",
        "No execution means no reproduced bug or verified fix.",
    ]
    if report.stage != "complete":
        lines += ["", "**INCOMPLETE INVESTIGATION**"]
    if report.is_example:
        lines += ["", "**SYNTHETIC EXAMPLE — not a live investigation**"]
    lines += [
        "",
        "## Identity",
        _block(
            f"Repository: {report.repository}\nRevision: {report.revision}\nComparison: {report.comparison_revision}\nModel: {report.model}"
        ),
    ]
    findings = {f.claim_id: f for f in report.findings}
    for claim in report.claims:
        lines += [
            "",
            "## Claim",
            _block(f"{claim.id}: {claim.text}\nReported as: {claim.reported_as}"),
        ]
        finding = findings.get(claim.id)
        if finding:
            lines += [
                f"Assessment: {finding.assessment}",
                _block(finding.explanation),
                "Evidence IDs:",
                _block("\n".join(finding.evidence_ids) or "None"),
                "Limitations:",
                _block("\n".join(finding.limitations) or "None recorded"),
                "Next step:",
                _block(finding.suggested_next_step or "None recorded"),
            ]
        else:
            lines += ["Assessment: not yet assessed"]
    for item in report.evidence:
        lines += [
            "",
            "## Evidence",
            _block(
                f"{item.id} | {item.kind}\n{item.revision}\n{item.path}:{item.start_line}-{item.end_line}\nExecution: {item.execution_id}"
            ),
            _block(item.excerpt),
        ]
    for run in report.executions:
        lines += [
            "",
            "## Execution",
            _block(
                f"{run.id} | {run.status}\nRevision: {run.revision}\nTest SHA256: {run.test_hash}\nCommand: {run.command}\nEnvironment: {run.environment}\nExit: {run.exit_code}\nDuration ms: {run.duration_ms}"
            ),
            "Output:",
            _block(run.stdout),
            "Errors:",
            _block(run.stderr),
        ]
    if report.errors:
        lines += ["", "## Analysis errors", _block("\n".join(report.errors))]
    return "\n\n".join(lines) + "\n"
