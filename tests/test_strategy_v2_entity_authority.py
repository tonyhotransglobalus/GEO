from scripts.strategy_engine_v2.entity_authority import (
    build_entity_authority_summary,
    normalize_entity_authority_payload,
)


def test_normalize_entity_authority_payload_keeps_mentions_and_profiles():
    payload = normalize_entity_authority_payload(
        {
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
                    "platform": "LinkedIn",
                    "mention_type": "company_profile",
                    "mention_url": "https://linkedin.com/company/transglobal/",
                    "entity_name": "TransGlobal",
                    "brand_match": "exact",
                    "source_quality_tier": "trusted_profile",
                    "profile_status": "complete",
                },
            ]
        }
    )

    assert len(payload["mentions"]) == 2
    assert payload["mentions"][0]["platform"] == "Reddit"
    assert payload["mentions"][1]["profile_status"] == "complete"


def test_build_entity_authority_summary_rolls_up_gaps():
    normalized = normalize_entity_authority_payload(
        {
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
    )

    summary = build_entity_authority_summary(normalized)

    assert summary["mention_count"] == 2
    assert summary["matched_mention_count"] == 1
    assert summary["gap_count"] == 2
