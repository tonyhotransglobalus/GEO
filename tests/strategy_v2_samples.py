def sample_v1_audit_payload() -> dict:
    return {
        "url": "https://www.transglobalus.com/",
        "brand_name": "TransGlobal Holding Company",
        "date": "2026-03-30",
        "geo_score": 52,
        "scores": {
            "ai_citability": 28,
            "brand_authority": 57,
            "content_eeat": 65,
            "technical": 80,
            "schema": 76,
            "platform_optimization": 48,
        },
        "platforms": {
            "ChatGPT": 53,
            "Perplexity": 53,
            "Gemini": 68,
        },
        "executive_summary": "TransGlobal is technically accessible but still weak on citation readiness.",
        "findings": [
            {
                "severity": "critical",
                "title": "Key pages are not AI-citation ready",
                "summary": "Average citability scored 28.0/100.",
                "leadership_impact": "Low citation readiness reduces the chance of appearing in AI answers.",
                "marketing_action": "Rewrite service pages into answer-first blocks.",
                "developer_action": "Support those pages with cleaner heading structure.",
                "observed_evidence": "The live audit measured average citability at 28.0/100.",
            }
        ],
        "query_clusters": [
            {
                "label": "life-insurance",
                "queries": ["life insurance"],
                "search_intent": "informational",
                "priority": "high",
                "related_entities": [],
                "metadata": {
                    "seed_topic": "life insurance",
                    "site_visible": False,
                    "opportunity_score": 82,
                    "serp_result_count": 6,
                    "top_domains": ["competitor.com", "publisher.com"],
                },
            }
        ],
        "citation_failures": [
            {
                "query": "life insurance",
                "target_url": "https://www.transglobalus.com/",
                "failure_mode": "non_visible_query",
                "evidence": [
                    "The site does not appear in the sampled SERP set.",
                    "Opportunity score: 82.",
                ],
                "recommended_fix": "Strengthen answer-first content and entity signals.",
                "metadata": {
                    "opportunity_score": 82,
                    "site_visible": False,
                    "label": "high",
                },
            }
        ],
        "crawler_access": {
            "GPTBot": {
                "platform": "OpenAI",
                "status": "Allowed By Default",
                "recommendation": "Keep accessible.",
            },
            "PerplexityBot": {
                "platform": "Perplexity",
                "status": "Allowed By Default",
                "recommendation": "Keep accessible.",
            },
        },
        "entity_graph": {
            "entity_name": "TransGlobal Holding Company",
            "canonical_url": "https://www.transglobalus.com/",
            "same_as": ["https://www.facebook.com/transglobalusa"],
            "related_entities": ["TransGlobal Holding Company"],
            "attributes": {"signals": ["schema", "same_as", "brand"]},
            "confidence": 0.85,
            "metadata": {"source": "site_snapshot_and_brand_data"},
        },
        "presentation_metadata": {
            "run_mode": "script-only",
            "driver": "script",
            "interactive": False,
        },
        "plugin_results": {
            "readiness": {
                "geo_scores": {
                    "geo_score": 52,
                    "scores": {
                        "ai_citability": 28,
                        "brand_authority": 57,
                        "content_eeat": 65,
                        "technical": 80,
                        "schema": 76,
                        "platform_optimization": 48,
                    },
                }
            }
        },
        "client_report_sections": {
            "competitive_benchmark": {
                "summary": "The benchmark sample is still partial, but named competitors were captured.",
                "competitor_set": ["competitor.com", "publisher.com"],
                "sample_scope": {
                    "platforms": ["ChatGPT", "Perplexity"],
                    "query_count": 6,
                    "date_range": "2026-03-30",
                    "locale": "en-US",
                    "sample_completeness": "partial",
                },
                "benchmark_rows": [
                    {
                        "competitor_name": "Competitor Co",
                        "platform": "ChatGPT",
                        "mention_share": "40%",
                        "citation_share": "20%",
                        "top_winning_queries": ["life insurance"],
                        "source_strength": "strong",
                        "sentiment_or_positioning": "Trusted comparison source",
                        "our_gap": "Missing answer-first service page",
                        "confidence": "medium",
                        "winning_domains": ["competitor.com"],
                    }
                ],
            },
            "platform_breakdown": {
                "platforms": [
                    {
                        "platform": "ChatGPT",
                        "documented_behavior": "Uses accessible, quotable source material.",
                        "observed_site_status": "Crawler access appears open.",
                        "observed_visibility_status": "Directional only in this run",
                        "cautious_inference": "Needs exact prompt captures for stronger proof.",
                        "recommended_actions": [
                            "Capture exact prompts and cited URLs for this platform."
                        ],
                        "official_sources": ["https://openai.com/gptbot"],
                        "last_verified_at": "2026-03-30",
                        "confidence": "low",
                    },
                    {
                        "platform": "Perplexity",
                        "documented_behavior": "Prefers cited sources and clear supporting domains.",
                        "observed_site_status": "Crawler access appears open.",
                        "observed_visibility_status": "Directional only in this run",
                        "cautious_inference": "Needs exact answer captures for stronger proof.",
                        "recommended_actions": [
                            "Capture exact prompts and cited URLs for this platform."
                        ],
                        "official_sources": ["https://docs.perplexity.ai/docs/resources/perplexity-crawlers"],
                        "last_verified_at": "2026-03-30",
                        "confidence": "low",
                    },
                ]
            },
            "prompt_query_proof": {
                "sampling_note": "Only one query capture was retained in this sample.",
                "rows": [
                    {
                        "query_or_prompt": "best life insurance company",
                        "query_theme": "life insurance",
                        "platform": "ChatGPT",
                        "model_surface": "chatgpt-search",
                        "locale": "en-US",
                        "capture_timestamp": "2026-03-30T10:00:00+00:00",
                        "brand_mentioned": False,
                        "brand_cited": False,
                        "winning_domains": ["competitor.com"],
                        "winning_urls": ["https://competitor.com/life"],
                        "response_summary": "Competitor Co was cited as the source.",
                        "why_we_lost_or_won": "TransGlobal lacked a quotable service page.",
                        "confidence": "medium",
                    }
                ],
            },
            "page_source_evidence": {
                "priority_pages": [
                    {
                        "page_url": "https://www.transglobalus.com/",
                        "page_type": "homepage",
                        "citability_score": 28,
                        "technical_observations": ["Observed H1 count: 10."],
                        "content_observations": ["Observed word count: 100."],
                        "schema_observations": ["Schema score: 76/100."],
                        "trust_observations": ["Entity confidence: 85/100."],
                        "recommended_fix": "Tighten answer-first structure and proof points.",
                        "confidence": "medium",
                    }
                ],
                "source_domains": [
                    {
                        "domain": "competitor.com",
                        "source_type": "competitor",
                        "why_it_matters": "Appears as a winner in sampled query results.",
                        "observed_role_in_answers": "Frequently cited competitor domain",
                        "gap_or_advantage": "Advantage",
                    }
                ],
                "entity_signal_review": {
                    "entity_name": "TransGlobal Holding Company",
                    "same_as_count": 1,
                    "confidence": 85,
                },
            },
            "action_plan_30_60_90": {
                "actions": [
                    {
                        "time_horizon": "30_days",
                        "action": "Rewrite key pages into answer-first blocks with facts and citations.",
                        "owner": "marketing",
                        "effort": "low",
                        "dependency": "Page ownership remains stable.",
                        "expected_outcome": "Re-measure AI citability after the content refresh.",
                        "success_metric": "Citability score improves on priority pages.",
                        "evidence_basis": "quick_wins",
                        "confidence": "medium",
                    }
                ]
            },
            "technical_proof_appendix": {
                "methodology": {
                    "summary": "Point-in-time GEO audit based on live crawl, content scoring, and visibility sampling.",
                    "confidence_note": "Useful as an early signal, but not a full benchmark in this run.",
                },
                "crawl_and_fetch_evidence": [
                    "Primary URL analyzed: https://www.transglobalus.com/."
                ],
                "robots_and_bot_access": [
                    "GPTBot (OpenAI): Allowed By Default. Recommendation: Keep accessible."
                ],
                "dom_and_heading_proof": ["Primary headings found on the page: 10."],
                "schema_proof": ["Structured data score: 76/100."],
                "source_inventory": ["competitor.com"],
                "limitations": {
                    "limitations_note": "The market view is directional, not a full benchmark."
                },
            },
        },
    }


def sample_v2_workflow_deps():
    from scripts.strategy_engine_v2.adjudication import adjudicate_v2_sections
    from scripts.strategy_engine_v2.evidence import build_v2_evidence_ledger
    from scripts.strategy_engine_v2.manifest import build_run_manifest
    from scripts.strategy_engine_v2.publish import publish_v2_artifacts
    from scripts.strategy_engine_v2.qa import run_release_checks
    from scripts.strategy_engine_v2.reporting import build_v2_report_sections
    from scripts.strategy_engine_v2.workflow import StrategyV2WorkflowDependencies

    return StrategyV2WorkflowDependencies(
        build_run_manifest=build_run_manifest,
        run_v1_audit=lambda **_kwargs: sample_v1_audit_payload(),
        build_v2_evidence_ledger=build_v2_evidence_ledger,
        adjudicate_v2_sections=adjudicate_v2_sections,
        build_v2_report_sections=build_v2_report_sections,
        run_release_checks=run_release_checks,
        publish_v2_artifacts=publish_v2_artifacts,
    )
