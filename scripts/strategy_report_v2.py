#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

try:
    from .strategy_engine_v2.workflow import run_strategy_report_v2
except ImportError:
    from strategy_engine_v2.workflow import run_strategy_report_v2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the V2 strategist workflow and generate the GEO report."
    )
    parser.add_argument("url", help="Target website URL")
    parser.add_argument(
        "--shadow-run",
        action="store_true",
        help="Run V2 in shadow mode without affecting V1 delivery.",
    )
    parser.add_argument(
        "--compare-to-v1",
        action="store_true",
        help="Include V1 comparison metadata in the run output.",
    )
    parser.add_argument(
        "--locale",
        default="en-us",
        help="Locale to use for the run.",
    )
    parser.add_argument(
        "--platform",
        action="append",
        default=[],
        help="Platform to sample. May be provided multiple times.",
    )
    parser.add_argument(
        "--competitor",
        action="append",
        default=[],
        help="Competitor domain to compare. May be provided multiple times.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt during the run.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    args = parse_args(argv)
    result = run_strategy_report_v2(
        args.url,
        shadow_run=args.shadow_run,
        compare_to_v1=args.compare_to_v1,
        locale=args.locale,
        platforms=args.platform,
        competitors=args.competitor,
        non_interactive=args.non_interactive,
    )
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
