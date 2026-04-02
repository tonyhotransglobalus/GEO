#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

try:
    from .full_audit import orchestrate_audit
    from .strategy_engine.guidance import load_guidance_snapshot
except ImportError:
    from full_audit import orchestrate_audit
    from strategy_engine.guidance import load_guidance_snapshot


def detect_agent_environment() -> tuple[str, str] | None:
    """Detect if the script is running within an agent-assisted IDE."""
    if os.getenv("ANTIGRAVITY"):
        return "agent-assisted", "antigravity"
    if os.getenv("CODEX"):
        return "agent-assisted", "codex"
    if os.getenv("GEMINI_CLI"):
        return "agent-assisted", "gemini"
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the strategist workflow and generate the GEO report."
    )
    env_defaults = detect_agent_environment()
    default_mode, default_driver = env_defaults if env_defaults else ("script-only", os.getenv("GEO_REPORT_DRIVER", "script"))

    parser.add_argument("url", help="Target website URL")
    parser.add_argument(
        "--mode",
        choices=("script-only", "agent-assisted"),
        default=default_mode,
        help="Record whether the run is script-only or agent-assisted.",
    )
    parser.add_argument(
        "--driver",
        default=default_driver,
        help="Record which runner launched the report, e.g. script, codex, gemini, antigravity.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("GEO_REPORT_MODEL"),
        help="Record the model identifier for agent-assisted runs, e.g. gpt-5.4 or gemini-2.5-pro.",
    )
    refresh_group = parser.add_mutually_exclusive_group()
    refresh_group.add_argument(
        "--refresh-guidance",
        action="store_true",
        help="Refresh the shared guidance snapshot before generating the report.",
    )
    refresh_group.add_argument(
        "--skip-guidance-refresh",
        action="store_true",
        help="Skip refreshing guidance and use the latest saved snapshot.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt for guidance refresh.",
    )
    return parser.parse_args(argv)


def is_interactive_session(args: argparse.Namespace) -> bool:
    return not args.non_interactive and bool(getattr(sys.stdin, "isatty", lambda: False)())


def resolve_guidance_refresh(
    args: argparse.Namespace,
    *,
    interactive: bool | None = None,
    input_func=input,
) -> bool:
    if args.refresh_guidance:
        return True
    if args.skip_guidance_refresh:
        return False
    if interactive is None:
        interactive = is_interactive_session(args)
    if not interactive:
        return False
    try:
        answer = input_func("Refresh shared guidance before generating the report? [y/N]: ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


def build_presentation_metadata(
    args: argparse.Namespace,
    guidance_snapshot: dict,
    *,
    refresh_requested: bool,
    interactive: bool,
) -> dict:
    official_sources: list[str] = []
    for platform in guidance_snapshot.get("platforms", []):
        if not isinstance(platform, dict):
            continue
        for source in platform.get("sources", []):
            if source and source not in official_sources:
                official_sources.append(source)
    return {
        "run_mode": args.mode,
        "driver": args.driver,
        "model": args.model,
        "interactive": interactive,
        "guidance": {
            "refresh_requested": refresh_requested,
            "source": guidance_snapshot.get("source"),
            "snapshot_path": guidance_snapshot.get("snapshot_path"),
            "reference_path": guidance_snapshot.get("reference_path"),
            "refreshed_at": guidance_snapshot.get("refreshed_at"),
            "official_sources": official_sources,
        },
    }


def main(argv: list[str] | None = None) -> dict:
    args = parse_args(argv)
    interactive = is_interactive_session(args)
    refresh_requested = resolve_guidance_refresh(args, interactive=interactive)
    guidance_snapshot = load_guidance_snapshot(refresh=refresh_requested)
    presentation_metadata = build_presentation_metadata(
        args,
        guidance_snapshot,
        refresh_requested=refresh_requested,
        interactive=interactive,
    )
    result = orchestrate_audit(
        args.url,
        presentation_metadata=presentation_metadata,
    )
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
