#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

try:
    from .full_audit import orchestrate_audit
except ImportError:
    from full_audit import orchestrate_audit


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the strategist workflow and generate the GEO report."
    )
    parser.add_argument("url", help="Target website URL")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    args = parse_args(argv)
    result = orchestrate_audit(args.url)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
