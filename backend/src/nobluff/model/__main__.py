"""Run: python -m nobluff.model --report issue.txt [--output claims.json]."""

import argparse
import sys
from pathlib import Path

from .extraction import MAX_REPORT_CHARS, ExtractionError, extract_claims


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract unverified claims with local Qwen."
    )
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        # Bound bytes read before decoding; library also enforces character limits.
        with args.report.open("rb") as stream:
            raw = stream.read(MAX_REPORT_CHARS * 4 + 1)
        if len(raw) > MAX_REPORT_CHARS * 4:
            raise ExtractionError(
                "input_too_large", "Report file exceeds the size limit."
            )
        result = extract_claims(raw.decode("utf-8"))
        output = result.model_dump_json(indent=2) + "\n"
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return 0
    except (OSError, UnicodeError):
        print(
            "Cannot read/write the requested UTF-8 file; check paths and permissions.",
            file=sys.stderr,
        )
    except ExtractionError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
