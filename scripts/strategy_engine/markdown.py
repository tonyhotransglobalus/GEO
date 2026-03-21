from __future__ import annotations

from .reporting import normalize_report_sections, report_sections_to_markdown


def render_markdown_report(data: dict) -> str:
    rescience = data.get("rescience_pass", {})
    report_sections = normalize_report_sections(data.get("report_sections"))

    lines = [
        f"# GEO Strategist Workbook: {data['brand_name']}",
        "",
        f"**Audit Date:** {data['date']}",
        f"**Primary URL:** {data['url']}",
        "",
        "---",
        "",
    ]

    if report_sections:
        lines.extend([report_sections_to_markdown(report_sections).strip(), ""])

    if data["findings"]:
        lines.extend(["---", "", "## Key Findings", ""])
        for finding in data["findings"]:
            summary = finding.get("summary") or finding.get("description", "")
            lines.extend(
                [
                    f"### [{finding['severity'].upper()}] {finding['title']}",
                    "",
                    summary,
                    "",
                    f"**Why this matters to leadership:** {finding.get('leadership_impact', 'Not provided.')}",
                    "",
                    f"**What marketing should do:** {finding.get('marketing_action', 'Not provided.')}",
                    "",
                    f"**What dev should change:** {finding.get('developer_action', 'Not provided.')}",
                    "",
                    f"**Observed evidence:** {finding.get('observed_evidence', 'Not provided.')}",
                    "",
                ]
            )
    else:
        lines.extend(["---", "", "## Key Findings", ""])
        lines.extend(["No critical findings recorded.", ""])

    lines.extend(["---", "", "## Prioritized Action Plan", ""])
    for title, items in (
        ("Quick Wins (This Week)", data.get("quick_wins", [])),
        ("Medium-Term Improvements (This Month)", data.get("medium_term", [])),
        ("Strategic Initiatives (This Quarter)", data.get("strategic", [])),
    ):
        lines.extend([f"### {title}", ""])
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("- None identified.")
        lines.append("")

    if rescience:
        lines.extend(["---", "", "## ReScience Optimization Pass", ""])
        if rescience.get("summary"):
            lines.extend([rescience["summary"], ""])

        priority_actions = rescience.get("priority_actions", {})
        if priority_actions:
            for priority in ("P0", "P1", "P2"):
                lines.extend([f"### {priority} Priorities", ""])
                items = priority_actions.get(priority, [])
                if items:
                    for item in items:
                        lines.append(f"- {item}")
                else:
                    lines.append("- None identified.")
                lines.append("")

        if rescience.get("platform_guidance"):
            lines.extend(["### Platform Guidance", ""])
            for platform, items in rescience["platform_guidance"].items():
                lines.append(f"#### {platform}")
                lines.append("")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        if rescience.get("geo_methods"):
            lines.extend(["### Recommended GEO Methods", ""])
            for method in rescience["geo_methods"]:
                recommendation = method.get("recommendation", "")
                suffix = f": {recommendation}" if recommendation else ""
                lines.append(
                    f"- **{method['method']}** ({method['impact']}){suffix}"
                )
            lines.append("")

    return "\n".join(lines).strip() + "\n"
