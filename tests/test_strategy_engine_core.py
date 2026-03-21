import unittest
from datetime import datetime

from scripts.strategy_engine import (
    AnalysisContext,
    CitationFailure,
    CompetitorProfile,
    EntityGraph,
    QueryCluster,
    ReportModel,
    SiteSnapshot,
    StrategyOrchestrator,
    StrategyPlugin,
    deserialize_report_model,
    serialize_report_model,
)


class StrategyEngineCoreTest(unittest.TestCase):
    def test_report_model_round_trip_preserves_nested_models(self):
        snapshot = SiteSnapshot(
            url="https://example.com",
            title="Example Co | GEO Strategy",
            canonical_url="https://example.com/",
            fetched_at="2026-03-19T10:00:00Z",
            language="en",
            word_count=842,
            headings=["Example Co", "What we do"],
            structured_data=[{"@type": "Organization", "name": "Example Co"}],
            internal_links=["https://example.com/about"],
            external_links=["https://www.linkedin.com/company/example"],
        )
        cluster = QueryCluster(
            label="core-intent",
            queries=["what is geo strategy"],
            search_intent="informational",
            priority="high",
        )
        competitor = CompetitorProfile(
            name="Competitor A",
            domain="competitor-a.com",
            source_urls=["https://competitor-a.com/services"],
            strengths=["clear positioning"],
            weaknesses=["thin citations"],
        )
        graph = EntityGraph(
            entity_name="Example Co",
            canonical_url="https://example.com",
            same_as=["https://www.linkedin.com/company/example"],
            related_entities=["Example Services"],
            confidence=0.83,
        )
        failure = CitationFailure(
            query="best geo strategy",
            target_url="https://example.com/guide",
            failure_mode="not surfaced in answer engines",
            evidence=["page not cited by retrieval results"],
            recommended_fix="add answer-first blocks and supporting citations",
        )
        report = ReportModel(
            brand_name="Example Co",
            site_snapshot=snapshot,
            query_clusters=[cluster],
            competitor_profiles=[competitor],
            entity_graph=graph,
            citation_failures=[failure],
            plugin_results={"stub": {"status": "ok"}},
            metadata={"source": "unit-test"},
        )

        data = serialize_report_model(report)
        restored = deserialize_report_model(data)

        self.assertEqual(restored, report)
        self.assertEqual(data["site_snapshot"]["url"], "https://example.com")
        self.assertEqual(data["query_clusters"][0]["label"], "core-intent")

    def test_orchestrator_runs_plugins_in_registration_order(self):
        class EchoPlugin(StrategyPlugin):
            name = "echo"

            def analyze(self, context: AnalysisContext):
                return {
                    "url": context.site_snapshot.url,
                    "cluster_count": len(context.query_clusters),
                }

        class LastPlugin(StrategyPlugin):
            name = "last"

            def analyze(self, context: AnalysisContext):
                return {"brand_name": context.report_model.brand_name}

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            query_clusters=[
                QueryCluster(
                    label="cluster",
                    queries=["geo strategy"],
                    search_intent="informational",
                )
            ],
        )

        orchestrator = StrategyOrchestrator()
        orchestrator.register_plugin(EchoPlugin())
        orchestrator.register_plugin(LastPlugin())

        result = orchestrator.execute(context)

        self.assertEqual(list(result.plugin_results.keys()), ["echo", "last"])
        self.assertEqual(result.plugin_results["echo"]["cluster_count"], 1)
        self.assertEqual(result.plugin_results["last"]["brand_name"], "Example Co")
        self.assertEqual(context.report_model.brand_name, "Example Co")

    def test_orchestrator_exposes_prior_plugin_results_to_later_plugins(self):
        class SeedPlugin(StrategyPlugin):
            name = "seed"

            def analyze(self, context: AnalysisContext):
                return {"status": "seeded"}

        class InspectPlugin(StrategyPlugin):
            name = "inspect"

            def analyze(self, context: AnalysisContext):
                return {
                    "seen_seed": context.report_model.plugin_results.get("seed", {}).get(
                        "status"
                    )
                }

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            )
        )

        orchestrator = StrategyOrchestrator([SeedPlugin(), InspectPlugin()])

        result = orchestrator.execute(context)

        self.assertEqual(result.plugin_results["inspect"]["seen_seed"], "seeded")
        self.assertEqual(
            context.report_model.plugin_results["seed"]["status"],
            "seeded",
        )

    def test_orchestrator_reflects_plugin_mutations_in_later_plugins(self):
        class MutateClustersPlugin(StrategyPlugin):
            name = "mutate_clusters"

            def analyze(self, context: AnalysisContext):
                context.query_clusters.append(
                    QueryCluster(
                        label="added",
                        queries=["geo strategy"],
                        search_intent="informational",
                    )
                )
                return {"cluster_count": len(context.query_clusters)}

        class ObserveClustersPlugin(StrategyPlugin):
            name = "observe_clusters"

            def analyze(self, context: AnalysisContext):
                return {
                    "cluster_count": len(context.report_model.query_clusters),
                    "last_cluster": context.report_model.query_clusters[-1].label,
                }

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            )
        )

        result = StrategyOrchestrator(
            [MutateClustersPlugin(), ObserveClustersPlugin()]
        ).execute(context)

        self.assertEqual(result.query_clusters[-1].label, "added")
        self.assertEqual(result.plugin_results["observe_clusters"]["cluster_count"], 1)
        self.assertEqual(result.plugin_results["observe_clusters"]["last_cluster"], "added")

    def test_orchestrator_honors_explicit_empty_list_sections(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            query_clusters=[],
            competitor_profiles=[],
            citation_failures=[],
        )
        context.report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=context.site_snapshot,
            query_clusters=[
                QueryCluster(
                    label="stale",
                    queries=["old query"],
                    search_intent="informational",
                )
            ],
            competitor_profiles=[
                CompetitorProfile(name="Stale Competitor", domain="old.example")
            ],
            citation_failures=[
                CitationFailure(query="old query", target_url="https://old.example")
            ],
        )

        orchestrator = StrategyOrchestrator()
        result = orchestrator.execute(context)

        self.assertEqual(result.query_clusters, [])
        self.assertEqual(result.competitor_profiles, [])
        self.assertEqual(result.citation_failures, [])

    def test_orchestrator_allows_explicit_entity_graph_clearing(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            entity_graph=None,
        )
        context.report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=context.site_snapshot,
            entity_graph=EntityGraph(
                entity_name="Example Co",
                canonical_url="https://example.com",
            ),
        )

        result = StrategyOrchestrator().execute(context)

        self.assertIsNone(result.entity_graph)

    def test_register_plugin_rejects_non_strategy_plugins(self):
        orchestrator = StrategyOrchestrator()

        with self.assertRaises(TypeError) as ctx:
            orchestrator.register_plugin(object())

        self.assertIn("StrategyPlugin", str(ctx.exception))

    def test_register_plugin_rejects_blank_plugin_name(self):
        class BlankNamePlugin(StrategyPlugin):
            name = "   "

            def analyze(self, context: AnalysisContext):
                return {}

        orchestrator = StrategyOrchestrator()

        with self.assertRaises(TypeError) as ctx:
            orchestrator.register_plugin(BlankNamePlugin())

        self.assertIn("non-empty string", str(ctx.exception))

    def test_analysis_context_defaults_keep_strategy_first_principles_enabled(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            )
        )

        self.assertTrue(context.generative_search_first)
        self.assertTrue(context.open_source_first)
        self.assertEqual(context.query_clusters, [])
        self.assertEqual(context.competitor_profiles, [])

    def test_plugin_results_datetime_values_are_serialized_to_json_safe_strings(self):
        class TimestampPlugin(StrategyPlugin):
            name = "timestamp"

            def analyze(self, context: AnalysisContext):
                return {"captured_at": datetime(2026, 3, 19, 10, 30, 0)}

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            )
        )

        result = StrategyOrchestrator([TimestampPlugin()]).execute(context)

        self.assertEqual(
            result.plugin_results["timestamp"]["captured_at"],
            "2026-03-19T10:30:00",
        )


if __name__ == "__main__":
    unittest.main()
