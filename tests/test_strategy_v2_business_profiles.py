from scripts.strategy_engine_v2.business_profiles import (
    infer_business_profile,
    resolve_business_profile,
)


def test_infer_business_profile_detects_local_signals():
    profile = infer_business_profile(
        {
            "google_business_profile": {"present": True},
            "locations": ["San Diego, CA"],
        }
    )

    assert profile == "local"


def test_infer_business_profile_detects_ecommerce_and_publisher_signals():
    assert infer_business_profile({"product_count": 12}) == "ecommerce"
    assert infer_business_profile({"content_type": "publisher"}) == "publisher"


def test_resolve_business_profile_keeps_explicit_profile():
    profile = resolve_business_profile("b2b_services", {"product_count": 12})

    assert profile["key"] == "b2b_services"
    assert profile["label"] == "B2B services"
