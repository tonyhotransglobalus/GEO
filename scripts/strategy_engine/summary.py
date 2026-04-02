from . import analysis

def build_rescience_pass(
    url: str,
    page_data: dict,
    citability_data: dict,
    llms_validation: dict,
    brand_data: dict,
) -> dict:
    priority_actions = {"P0": [], "P1": [], "P2": []}
    
    brand_name = (brand_data or {}).get("brand_name")
    text_content = str(page_data.get("text_content") or "")
    
    # Advanced analysis for ReScience pass
    analysis_result = analysis.analyze_block_citability(text_content, brand_name)
    geo_methods = analysis.get_geo_methods(analysis_result)

    if page_data.get("status_code") != 200:
        priority_actions["P0"].append("Restore homepage accessibility and eliminate 5xx or unreachable states.")

    if not page_data.get("has_ssr_content"):
        priority_actions["P0"].append("Add server-rendered content so crawlers can see meaningful HTML without JavaScript.")

    if (
        not llms_validation.get("exists")
        or not llms_validation.get("format_valid")
        or llms_validation.get("issues")
    ):
        priority_actions["P2"].append(
            "Consider publishing llms.txt and llms-full.txt as optional AI discoverability hints for supported platforms."
        )

    if len(page_data.get("h1_tags", [])) != 1:
        priority_actions["P1"].append("Normalize heading hierarchy so each page has a single H1.")

    if citability_data.get("average_citability_score", 0) < 50:
        priority_actions["P1"].append("Rewrite key pages into answer-first blocks with facts, citations, and concise paragraphs.")

    # Advanced Analysis-Driven Actions
    metrics = analysis_result.get("metrics", {})
    if metrics.get("answer_block_score", 0) < 60:
        priority_actions["P1"].append("Structure key sections as concise, self-contained 'Answer Blocks' (40-60 words) for direct AI retrieval.")
    
    if metrics.get("self_contain_score", 0) < 50:
        priority_actions["P1"].append("Increase content self-containment; ensure 'Answer Blocks' remain accurate even when extracted from their surrounding context.")
    
    if metrics.get("fact_density", 0) < 0.3:
        priority_actions["P1"].append("Fact density is below GEO benchmarks. Target 1-2 specific entities or data points per 'Answer Block'.")

    security_headers = page_data.get("security_headers", {})

    if not security_headers.get("Content-Security-Policy"):
        priority_actions["P2"].append("Add stronger security headers, starting with Content-Security-Policy.")

    wiki = ((brand_data or {}).get("platforms") or {}).get("wikipedia") or {}
    if not (wiki.get("has_wikipedia_page") or wiki.get("has_wikidata_entry")):
        priority_actions["P2"].append("Strengthen entity trust with consistent profiles, citations, and a future Wikidata path if eligible.")

    platform_guidance = {
        "ChatGPT": [
            "Keep high-value pages accessible to OAI-SearchBot when you want them surfaced in ChatGPT search experiences.",
            "Refresh high-value pages regularly and keep answer blocks factual, attributable, and quotable.",
        ],
        "Perplexity": [
            "Keep PerplexityBot accessible where you want search visibility, and review WAF settings if crawl access looks inconsistent.",
            "Use concise answer blocks, comparisons, and cited explainers that Perplexity can quote clearly.",
        ],
        "Google AI Overviews": [
            "No special AI file is required for Google visibility.",
            "Focus on the same core signals as modern SEO: crawlable content, clear page purpose, strong citations, and useful structured data.",
        ],
        "Bing Copilot": [
            "Preserve Bing crawlability and prefer official Bing AI Performance data when it is available.",
            "Improve entity clarity across site content and external profiles so Bing has cleaner grounding signals.",
        ],
        "Claude": [
            "Keep ClaudeBot and Claude-SearchBot access aligned with your intended discovery posture.",
            "Increase factual density and structural clarity so retrieved snippets are easier to cite accurately.",
        ],
    }

    summary_parts = [
        "ReScience optimization pass focuses on actionable SEO/GEO execution rather than a second weighted score."
    ]
    if not llms_validation.get("exists"):
        summary_parts.append(
            "An optional llms.txt discoverability hint is not yet published for platforms that may use it."
        )
    if citability_data.get("average_citability_score", 0) < 50:
        summary_parts.append("The biggest content gap is weak answer-first formatting and low factual density.")

    return {
        "url": url,
        "summary": " ".join(summary_parts),
        "priority_actions": priority_actions,
        "platform_guidance": platform_guidance,
        "geo_methods": geo_methods,
    }


def build_findings(
    page_data: dict,
    citability_data: dict,
    llms_live: dict,
    llms_validation: dict,
    brand_data: dict,
    rescience_pass: dict,
) -> list[dict]:
    findings = []
    average_citability = citability_data.get("average_citability_score", 0)
    heading_count = len(page_data.get("h1_tags", []))

    def add_finding(
        *,
        severity: str,
        title: str,
        summary: str,
        leadership_impact: str,
        marketing_action: str,
        developer_action: str,
        observed_evidence: str,
    ) -> None:
        findings.append(
            {
                "severity": severity,
                "title": title,
                "summary": summary,
                "description": summary,
                "leadership_impact": leadership_impact,
                "marketing_action": marketing_action,
                "developer_action": developer_action,
                "observed_evidence": observed_evidence,
            }
        )

    if average_citability < 50:
        add_finding(
            severity="critical",
            title="Key pages are not AI-citation ready",
            summary=(
                f"Average citability scored {average_citability}/100, which means priority pages are still weak candidates "
                "for extraction into AI-generated answers."
            ),
            leadership_impact=(
                "Low citation readiness reduces the brand's chance of appearing in AI answers during high-intent discovery, "
                "which directly limits awareness, assisted conversion, and competitive share of voice."
            ),
            marketing_action=(
                "Rewrite service, solution, and explainer pages into answer-first sections with sourced statistics, "
                "clear proof points, and short extractable paragraphs."
            ),
            developer_action=(
                "Support content templates with one clear H1, stronger H2/H3 structure, and reusable placements for FAQ "
                "and supporting schema on high-priority pages."
            ),
            observed_evidence=(
                f"The live audit measured average citability at {average_citability}/100, below the threshold where pages "
                "are typically easy for AI systems to quote and attribute."
            ),
        )

    llms_exists = llms_live.get("llms_txt", {}).get("exists")
    llms_valid = bool(llms_validation.get("format_valid")) and not llms_validation.get(
        "issues"
    )

    if not llms_exists:
        add_finding(
            severity="medium",
            title="llms.txt guidance files are missing",
            summary=(
                "The site does not expose llms.txt guidance files at the root. This is an optional discoverability hint for "
                "some platforms, not a universal requirement."
            ),
            leadership_impact=(
                "Missing llms.txt can limit optional discoverability hints for certain AI platforms, but it is usually less important "
                "than crawlability, page clarity, citations, and entity trust."
            ),
            marketing_action=(
                "Publish llms.txt and llms-full.txt if you want an additional machine-readable inventory of priority pages for "
                "platforms that may consult it."
            ),
            developer_action=(
                "Treat llms.txt as an optional maintained artifact, version it with the site, and keep it aligned with the current "
                "priority URL set if you decide to ship it."
            ),
            observed_evidence=(
                "The live fetch did not find llms.txt at the expected root path, so this optional guidance file is not currently published."
            ),
        )
    elif not llms_valid:
        add_finding(
            severity="medium",
            title="llms.txt guidance files are present but malformed",
            summary=(
                "The site exposes llms.txt guidance files, but validation shows the guidance is incomplete or malformed."
            ),
            leadership_impact=(
                "A malformed optional guidance file creates false confidence because it looks maintained without reliably helping the platforms that may read it."
            ),
            marketing_action=(
                "Repair llms.txt and llms-full.txt so they include the expected title, description, section structure, and page links."
            ),
            developer_action=(
                "Update the generated guidance files and keep validation in the release workflow so malformed guidance does not ship."
            ),
            observed_evidence=(
                "The live fetch found llms.txt, but validation flagged format issues, so the guidance layer is present without being fully usable."
            ),
        )

    if heading_count != 1:
        add_finding(
            severity="high",
            title="Heading architecture is diluted",
            summary=(
                f"The homepage currently exposes {heading_count} H1 tags instead of one clear primary page thesis, "
                "which weakens how both users and AI systems interpret topical focus."
            ),
            leadership_impact=(
                "A diluted page thesis makes the brand's most important landing page less clear, which can suppress message retention "
                "and reduce AI confidence in the page's core topic."
            ),
            marketing_action=(
                "Clarify the homepage message hierarchy so the primary value proposition is unmistakable, then align supporting sections "
                "to secondary audience and service themes."
            ),
            developer_action=(
                "Refactor heading markup to a single H1 with semantically ordered H2 and H3 sections, and remove layout-driven heading misuse."
            ),
            observed_evidence=(
                f"The homepage audit found {heading_count} H1 tags, a strong sign that content hierarchy is being split across multiple competing signals."
            ),
        )

    if rescience_pass["priority_actions"]["P2"]:
        add_finding(
            severity="medium",
            title="Optimization opportunities remain after the base audit",
            summary=rescience_pass["summary"],
            leadership_impact=(
                "The site has a workable foundation, but unresolved optimization gaps will keep the brand from reaching stronger AI visibility gains "
                "without a coordinated follow-through plan."
            ),
            marketing_action=(
                "Turn the ReScience recommendations into an execution backlog for content refreshes, proof-point additions, and platform-specific improvements."
            ),
            developer_action=(
                "Bundle the structural recommendations into roadmap work so schema, content modules, and technical trust signals are implemented consistently."
            ),
            observed_evidence=(
                "The advisory pass still flagged medium-priority optimization work, which indicates the site can improve even after the baseline audit score is calculated."
            ),
        )

    wiki = ((brand_data or {}).get("platforms") or {}).get("wikipedia") or {}
    if not (wiki.get("has_wikipedia_page") or wiki.get("has_wikidata_entry")):
        add_finding(
            severity="medium",
            title="Entity trust signals are still thin",
            summary=(
                "Brand identity appears across social platforms, but stronger authoritative entity reinforcement is still missing."
            ),
            leadership_impact=(
                "Thin entity trust makes it harder for AI systems to confidently associate the brand with its services, expertise, and authority."
            ),
            marketing_action=(
                "Strengthen third-party validation through consistent profile governance, citation-worthy proof points, and broader entity reinforcement across trusted platforms."
            ),
            developer_action=(
                "Align visible profile links, organization schema, and sameAs references so the site publishes one consistent entity graph."
            ),
            observed_evidence=(
                "The audit found social presence but did not confirm stronger authority anchors such as Wikipedia or Wikidata-level entity reinforcement."
            ),
        )

    return findings


def build_action_lists(rescience_pass: dict) -> tuple[list[str], list[str], list[str]]:
    quick_wins = rescience_pass["priority_actions"]["P1"][:5]
    medium_term = rescience_pass["priority_actions"]["P2"][:5]
    strategic = [
        "Build recurring AI-native content that answers high-intent user questions directly.",
        "Develop stronger entity authority through third-party citations and consistent profile governance.",
        "Track AI visibility, referral traffic, and citation wins as ongoing GEO KPIs.",
    ]
    return quick_wins, medium_term, strategic


def build_crawler_access(robots_data: dict) -> dict:
    crawler_map = {
        "GPTBot": "OpenAI",
        "OAI-SearchBot": "OpenAI search",
        "ChatGPT-User": "ChatGPT browse",
        "ClaudeBot": "Claude",
        "Claude-SearchBot": "Claude search",
        "PerplexityBot": "Perplexity",
        "Perplexity-User": "Perplexity user fetch",
        "Google-Extended": "Gemini",
        "Applebot-Extended": "Apple",
    }
    access = {}
    for crawler, platform in crawler_map.items():
        status = robots_data.get("ai_crawler_status", {}).get(crawler, "Unknown")
        normalized = status.replace("_", " ").title()
        if crawler in {"ChatGPT-User", "Perplexity-User"}:
            recommendation = "Review app fetch behavior and logs; user-triggered fetches may not behave like standard crawlers."
        else:
            recommendation = "Keep accessible." if "Allow" in normalized else "Review access."
        access[crawler] = {
            "platform": platform,
            "status": normalized,
            "recommendation": recommendation,
        }
    return access


def build_executive_summary(
    brand_name: str,
    geo_score: int,
    page_data: dict,
    citability_data: dict,
    llms_live: dict,
    llms_validation: dict,
    rescience_pass: dict,
) -> str:
    llms_exists = llms_live.get("llms_txt", {}).get("exists")
    llms_valid = bool(llms_validation.get("format_valid")) and not llms_validation.get(
        "issues"
    )
    heading_count = len(page_data.get("h1_tags", []))
    summary = [
        f"A live GEO audit of {brand_name} found a technically accessible site with a GEO score of {geo_score}/100.",
        "The numeric score comes from the geo-seo-claude audit model, while the advisory recommendations come from a separate ReScience optimization pass.",
        f"The most urgent content issue is low citability at {citability_data.get('average_citability_score', 0)}/100.",
    ]
    if not llms_exists:
        summary.append("An optional llms.txt guidance file is not published, but the larger visibility priorities remain crawlability, strong answers, and entity clarity.")
    elif not llms_valid:
        summary.append("An optional llms.txt guidance file exists but needs cleanup before it can serve as a reliable discoverability hint.")
    if heading_count != 1:
        summary.append(f"The homepage also needs cleaner information architecture because it currently exposes {heading_count} H1 tags.")
    summary.append(rescience_pass["summary"])
    return " ".join(summary)
