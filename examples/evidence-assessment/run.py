"""Run a real local model against labelled synthetic source evidence."""

import json
from pathlib import Path

from nobluff.model import assess_claims
from nobluff.schemas import Claim, Evidence

root = Path(__file__).resolve().parent
data = json.loads((root / "input.json").read_text())
result = assess_claims(
    [Claim.model_validate(c) for c in data["claims"]],
    [Evidence.model_validate(e) for e in data["evidence"]],
)
(root / "actual-output.json").write_text(result.model_dump_json(indent=2) + "\n")
print(result.model_dump_json(indent=2))
