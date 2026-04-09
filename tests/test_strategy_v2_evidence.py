from scripts.strategy_engine_v2.evidence import (
    build_citability_evidence,
    build_evidence_item,
    build_v2_evidence_ledger,
)
from tests.strategy_v2_samples import sample_v1_audit_payload


def test_build_evidence_item_marks_observed_vs_inferred():
    item = build_evidence_item(
        evidence_type="page_citability",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme="life insurance",
        url_or_domain="https://www.transglobalus.com/",
        raw_observation={"score": 28},
        normalized_summary="Citability is weak on the homepage.",
        confidence="medium",
    )

    assert item["source_class"] == "live_site"
    assert item["observed_vs_inferred"] == "observed"


def test_build_v2_evidence_ledger_ingests_multiple_sources():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True},
            "platforms": ["chatgpt"],
            "competitors": ["example.com"],
        },
        page_data={"title": "TransGlobal"},
        robots_data={"gptbot": "allowed"},
        llms_data={"found": False},
        citability_data={"score": 28},
        brand_data={"entity_score": 71},
        plugin_results={"readiness": "ok"},
    )

    assert ledger["count"] == 7
    assert [item["evidence_type"] for item in ledger["items"]] == [
        "run_manifest",
        "page_fetch",
        "robots",
        "llms",
        "page_citability",
        "brand_entity",
        "plugin_results",
    ]


def test_build_v2_evidence_ledger_keeps_empty_payloads():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": [],
            "competitors": [],
        },
        page_data={},
        robots_data={},
        llms_data={},
        citability_data={},
        brand_data={},
        plugin_results={},
    )

    assert ledger["count"] == 7
    assert [item["evidence_type"] for item in ledger["items"]] == [
        "run_manifest",
        "page_fetch",
        "robots",
        "llms",
        "page_citability",
        "brand_entity",
        "plugin_results",
    ]


def test_build_citability_evidence_is_computed():
    item = build_citability_evidence(
        {"score": 28},
        url="https://www.transglobalus.com/",
    )

    assert item["source_class"] == "internal_score"
    assert item["observed_vs_inferred"] == "inferred"


def test_build_v2_evidence_ledger_does_not_confuse_finding_severity_with_confidence():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": [],
            "competitors": [],
        },
        audit_data={
            "findings": [
                {
                    "severity": "critical",
                    "title": "Heading Architecture Is Diluted",
                    "summary": "Homepage exposes 10 H1 tags.",
                }
            ]
        },
    )

    finding_item = next(
        item for item in ledger["items"] if item["evidence_type"] == "finding"
    )
    assert finding_item["confidence"] == "medium"


def test_build_v2_evidence_ledger_reuses_v1_audit_sections():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True, "eligible": True},
            "platforms": ["ChatGPT", "Perplexity"],
            "competitors": ["competitor.com"],
        },
        audit_data=sample_v1_audit_payload(),
    )

    evidence_types = [item["evidence_type"] for item in ledger["items"]]
    assert "query_cluster" in evidence_types
    assert "citation_failure" in evidence_types
    assert "benchmark_row" in evidence_types
    assert "platform_observation" in evidence_types
    assert "prompt_proof" in evidence_types
    assert "priority_page" in evidence_types


def test_build_v2_evidence_ledger_synthesizes_sampled_prompt_proof_when_exact_rows_are_missing():
    audit_data = sample_v1_audit_payload()
    audit_data["client_report_sections"]["prompt_query_proof"] = {
        "sampling_note": "Exact platform captures were not retained in this sample.",
        "rows": [],
    }

    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True, "eligible": True},
            "platforms": ["ChatGPT", "Perplexity"],
            "competitors": ["competitor.com"],
        },
        audit_data=audit_data,
    )

    prompt_proof_items = [
        item for item in ledger["items"] if item["evidence_type"] == "prompt_proof"
    ]
    assert prompt_proof_items
    assert prompt_proof_items[0]["observed_vs_inferred"] == "inferred"
    assert (
        prompt_proof_items[0]["raw_observation"]["capture_mode"]
        == "sampled_query_bridge"
    )


def test_build_v2_evidence_ledger_captures_internal_page_breadth():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True, "eligible": True},
            "platforms": [],
            "competitors": [],
        },
        page_data={
            "title": "TransGlobal",
            "internal_links": [
                {"url": "https://www.transglobalus.com/"},
                {"url": "https://www.transglobalus.com/life-insurance-annuity/", "text": "Life & Annuities"},
                {"url": "https://www.transglobalus.com/wealth-management/", "text": "Advisory"},
            ],
        },
    )

    linked_pages = [
        item for item in ledger["items"] if item["evidence_type"] == "linked_page"
    ]
    assert len(linked_pages) == 2
    assert {
        item["url_or_domain"] for item in linked_pages
    } == {
        "https://www.transglobalus.com/life-insurance-annuity/",
        "https://www.transglobalus.com/wealth-management/",
    }


def test_build_v2_evidence_ledger_filters_low_signal_page_noise():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True, "eligible": True},
            "platforms": [],
            "competitors": [],
        },
        audit_data={
            "plugin_results": {
                "readiness": {
                    "inputs": {
                        "sitemap_pages": [
                            "https://www.transglobalus.com/zh/example-page/",
                            "https://www.transglobalus.com/category/financial/",
                        ]
                    }
                }
            }
        },
        page_data={
            "title": "TransGlobal",
            "internal_links": [
                {"url": "https://www.transglobalus.com/life-insurance-annuity/", "text": "Life & Annuities"},
                {"url": "https://www.transglobalus.com/author/admin/", "text": "admin"},
                {"url": "https://www.transglobalus.com/category/financial/", "text": "Financial News"},
                {"url": "https://www.transglobalus.com/treasury-rally-offers-mortgage-market-brief-relief-amid-war-jitters/", "text": ""},
            ],
        },
    )

    linked_pages = [
        item["url_or_domain"]
        for item in ledger["items"]
        if item["evidence_type"] == "linked_page"
    ]
    assert linked_pages == ["https://www.transglobalus.com/life-insurance-annuity/"]


def test_build_v2_evidence_ledger_models_platform_control_surfaces():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": ["ChatGPT", "Claude", "Perplexity", "Google"],
            "competitors": [],
        },
        audit_data={
            "date": "2026-04-03",
            "crawler_access": {
                "OAI-SearchBot": {"platform": "OpenAI", "status": "Allowed By Default", "recommendation": "Keep accessible."},
                "GPTBot": {"platform": "OpenAI", "status": "Blocked in robots.txt", "recommendation": "Keep blocked until training policy is defined."},
                "Claude-SearchBot": {"platform": "Anthropic", "status": "Allowed By Default", "recommendation": "Keep accessible."},
                "ClaudeBot": {"platform": "Anthropic", "status": "Blocked in robots.txt", "recommendation": "Allow only if training access is approved."},
                "Claude-User": {"platform": "Anthropic", "status": "Allowed By Default", "recommendation": "Review app fetch behavior separately."},
                "PerplexityBot": {"platform": "Perplexity", "status": "Allowed By Default", "recommendation": "Keep accessible."},
                "Perplexity-User": {"platform": "Perplexity", "status": "Review in WAF", "recommendation": "Allow app fetch traffic if users rely on Perplexity answers."},
                "Google-Extended": {"platform": "Google", "status": "Disallowed", "recommendation": "Keep blocked unless AI usage policy changes."},
            },
        },
    )

    control_items = [
        item["raw_observation"]
        for item in ledger["items"]
        if item["evidence_type"] == "platform_control"
    ]

    openai_search = next(item for item in control_items if item["bot_name"] == "OAI-SearchBot")
    openai_training = next(item for item in control_items if item["bot_name"] == "GPTBot")
    openai_user_fetch = next(item for item in control_items if item["platform"] == "ChatGPT" and item["surface"] == "user_fetch")
    perplexity_user_fetch = next(item for item in control_items if item["bot_name"] == "Perplexity-User")
    google_extended = next(item for item in control_items if item["bot_name"] == "Google-Extended")

    assert openai_search["surface"] == "search_bot"
    assert openai_search["status"] == "Allowed"
    assert openai_training["surface"] == "training_bot"
    assert openai_training["status"] == "Blocked"
    assert openai_user_fetch["status"] == "Not observed"
    assert "app fetch" in openai_user_fetch["recommendation"].lower()
    assert "openai.com" in openai_search["source_url"]
    assert openai_training["impact_if_blocked"]
    assert perplexity_user_fetch["surface"] == "user_fetch"
    assert perplexity_user_fetch["status"] == "Review"
    assert "perplexity.ai" in perplexity_user_fetch["source_url"]
    assert google_extended["surface"] == "ai_usage"
    assert google_extended["status"] == "Blocked"


def test_build_v2_evidence_ledger_captures_freshness_authorship_and_accessibility():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/insights/retirement-income/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": [],
            "competitors": [],
        },
        page_data={
            "title": "Retirement Income Planning",
            "byline": "Jane Doe, CFP",
            "author_pages": ["https://www.transglobalus.com/authors/jane-doe/"],
            "structured_data": [
                {
                    "@type": "Article",
                    "datePublished": "2026-03-01",
                    "dateModified": "2026-03-20",
                    "author": {"name": "Jane Doe, CFP"},
                }
            ],
            "aria_landmarks": ["banner", "navigation", "main", "contentinfo"],
            "rendered_state_parity": {
                "status": "partial",
                "summary": "Primary CTA only appears after hydration.",
            },
        },
    )

    evidence_by_type = {
        item["evidence_type"]: item
        for item in ledger["items"]
        if item["evidence_type"] in {"freshness_signal", "authorship_signal", "accessibility_signal"}
    }

    freshness = evidence_by_type["freshness_signal"]["raw_observation"]
    authorship = evidence_by_type["authorship_signal"]["raw_observation"]
    accessibility = evidence_by_type["accessibility_signal"]["raw_observation"]
    freshness_item = evidence_by_type["freshness_signal"]
    authorship_item = evidence_by_type["authorship_signal"]
    accessibility_item = evidence_by_type["accessibility_signal"]

    assert freshness["date_published"] == "2026-03-01"
    assert freshness["date_modified"] == "2026-03-20"
    assert freshness_item["confidence"] == "medium"
    assert authorship["byline"] == "Jane Doe, CFP"
    assert authorship["author_pages"] == ["https://www.transglobalus.com/authors/jane-doe/"]
    assert authorship_item["confidence"] == "medium"
    assert accessibility["aria_landmarks"] == ["banner", "navigation", "main", "contentinfo"]
    assert accessibility["rendered_state_parity_status"] == "partial"
    assert accessibility_item["confidence"] == "medium"


def test_build_v2_evidence_ledger_hardens_task4_contract_fields():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/insights/retirement-income/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": [],
            "competitors": [],
        },
        audit_data={"date": "2026-04-08"},
        page_data={
            "title": "Retirement Income Planning",
            "byline": "Jane Doe, CFP",
            "author_pages": ["https://www.transglobalus.com/authors/jane-doe/"],
            "visible_dates": [
                {"text": "Updated March 20, 2026", "source": "page_header"}
            ],
            "structured_data": [
                {
                    "@type": "Article",
                    "datePublished": "2026-03-01",
                    "dateModified": "2026-03-20",
                    "author": {"name": "Jane Doe, CFP"},
                }
            ],
            "aria_landmarks": ["banner", "navigation", "main", "contentinfo"],
            "main_landmark_count": 1,
            "rendered_state_parity": {
                "status": "partial",
                "summary": "Primary CTA only appears after hydration.",
                "missing_elements": ["cta-primary"],
                "rendered_only_content_detected": True,
            },
        },
    )

    evidence_by_type = {
        item["evidence_type"]: item
        for item in ledger["items"]
        if item["evidence_type"] in {"freshness_signal", "authorship_signal", "accessibility_signal"}
    }

    freshness = evidence_by_type["freshness_signal"]["raw_observation"]
    authorship = evidence_by_type["authorship_signal"]["raw_observation"]
    accessibility = evidence_by_type["accessibility_signal"]["raw_observation"]

    assert freshness["visible_date_text"] == "Updated March 20, 2026"
    assert freshness["visible_date_source"] == "page_header"
    assert freshness["schema_date_source"] == "Article.datePublished/dateModified"
    assert freshness["date_alignment_status"] == "aligned"
    assert freshness["staleness_bucket"] == "recent_90d"
    assert freshness["comparability_key"] == "freshness_signal:v2"

    assert authorship["visible_byline_present"] is True
    assert authorship["schema_author_present"] is True
    assert authorship["author_alignment_status"] == "aligned"
    assert authorship["credentials_visible"] is True
    assert authorship["author_page_status"] == "present"
    assert authorship["comparability_key"] == "authorship_signal:v2"

    assert accessibility["single_main_status"] == "pass"
    assert accessibility["landmark_count"] == 4
    assert accessibility["parity_failure_elements"] == ["cta-primary"]
    assert accessibility["rendered_only_content_detected"] is True
    assert accessibility["comparability_key"] == "accessibility_signal:v2"


def test_build_v2_evidence_ledger_downgrades_conflicting_or_missing_task4_proof():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/insights/retirement-income/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": [],
            "competitors": [],
        },
        audit_data={"date": "2026-04-08"},
        page_data={
            "title": "Retirement Income Planning",
            "byline": "John Smith",
            "author_pages": [],
            "visible_dates": [
                {"text": "Updated March 20, 2026", "source": "page_header"}
            ],
            "structured_data": [
                {
                    "@type": "Article",
                    "datePublished": "2025-01-01",
                    "dateModified": "2025-01-05",
                    "author": {"name": "Jane Doe, CFP"},
                }
            ],
            "aria_landmarks": ["banner", "navigation", "contentinfo"],
            "main_landmark_count": 0,
            "rendered_state_parity": {
                "status": "partial",
                "summary": "Primary CTA only appears after hydration.",
                "missing_elements": ["cta-primary"],
                "rendered_only_content_detected": True,
            },
        },
    )

    evidence_by_type = {
        item["evidence_type"]: item
        for item in ledger["items"]
        if item["evidence_type"] in {"freshness_signal", "authorship_signal", "accessibility_signal"}
    }

    freshness = evidence_by_type["freshness_signal"]
    authorship = evidence_by_type["authorship_signal"]
    accessibility = evidence_by_type["accessibility_signal"]

    assert freshness["raw_observation"]["date_alignment_status"] == "conflict"
    assert freshness["raw_observation"]["staleness_bucket"] == "stale_gt_year"
    assert freshness["confidence"] == "low"

    assert authorship["raw_observation"]["author_alignment_status"] == "conflict"
    assert authorship["raw_observation"]["author_page_status"] == "missing"
    assert authorship["confidence"] == "low"

    assert accessibility["raw_observation"]["single_main_status"] == "missing"


def test_build_v2_evidence_ledger_includes_platform_measurement_evidence():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": ["Bing", "ChatGPT"],
            "competitors": [],
        },
        audit_data={
            "measurement_data": {
                "platforms": [
                    {
                        "platform": "Bing",
                        "source": "bing_ai_performance",
                        "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
                        "page_metrics": [
                            {
                                "page_url": "https://www.transglobalus.com/retirement-income/",
                                "cited_count": 7,
                                "grounding_queries": ["best retirement income strategy", "retirement income planning"],
                            }
                        ],
                    },
                    {
                        "platform": "ChatGPT",
                        "source": "chatgpt_referrals",
                        "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
                        "referrals": {"visits": 42, "change_pct": 18.5, "utm_source": "chatgpt.com"},
                    },
                ]
            }
        },
    )

    evidence_types = [item["evidence_type"] for item in ledger["items"]]
    assert "platform_measurement" in evidence_types
    assert "citation_share_signal" in evidence_types
    assert "referral_signal" in evidence_types

    platform_measurement = next(
        item for item in ledger["items"] if item["evidence_type"] == "platform_measurement" and item["platform"] == "Bing"
    )
    citation_signal = next(
        item for item in ledger["items"] if item["evidence_type"] == "citation_share_signal"
    )
    referral_signal = next(
        item for item in ledger["items"] if item["evidence_type"] == "referral_signal"
    )

    assert platform_measurement["raw_observation"]["citation_count"] == 7
    assert platform_measurement["raw_observation"]["grounding_query_count"] == 2
    assert citation_signal["url_or_domain"] == "https://www.transglobalus.com/retirement-income/"
    assert referral_signal["raw_observation"]["visits"] == 42


def test_build_v2_evidence_ledger_includes_offsite_entity_authority_evidence():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": [],
            "competitors": [],
        },
        audit_data={
            "entity_authority_data": {
                "mentions": [
                    {
                        "platform": "Reddit",
                        "mention_type": "discussion",
                        "mention_url": "https://reddit.com/r/retirement/comments/example",
                        "entity_name": "TransGlobal",
                        "brand_match": "exact",
                        "source_quality_tier": "community",
                        "profile_status": "present",
                    },
                    {
                        "platform": "Wikipedia",
                        "mention_type": "entity_profile",
                        "mention_url": "https://wikipedia.org/wiki/TransGlobal",
                        "entity_name": "TransGlobal",
                        "brand_match": "partial",
                        "source_quality_tier": "reference",
                        "profile_status": "thin",
                    },
                ]
            }
        },
    )

    evidence_types = [item["evidence_type"] for item in ledger["items"]]
    assert "offsite_entity_signal" in evidence_types
    assert "offsite_authority_gap" in evidence_types

    wikipedia_gap = next(
        item
        for item in ledger["items"]
        if item["evidence_type"] == "offsite_authority_gap"
        and item["raw_observation"]["platform"] == "Wikipedia"
    )
    reddit_signal = next(
        item
        for item in ledger["items"]
        if item["evidence_type"] == "offsite_entity_signal" and item["platform"] == "Reddit"
    )

    assert wikipedia_gap["raw_observation"]["platform"] == "Wikipedia"
    assert reddit_signal["url_or_domain"] == "https://reddit.com/r/retirement/comments/example"
