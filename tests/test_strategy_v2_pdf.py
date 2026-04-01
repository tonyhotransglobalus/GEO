from pathlib import Path

from PyPDF2 import PdfReader

from scripts.strategy_engine_v2.workflow import run_strategy_report_v2
from tests.strategy_v2_samples import sample_v2_workflow_deps


def test_v2_pdf_renders_core_sections(tmp_path):
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        shadow_run=False,
        compare_to_v1=True,
        reports_dir=tmp_path,
        deps=sample_v2_workflow_deps(),
    )

    pdf_path = Path(result["artifact_paths"]["pdf_path"])
    assert pdf_path.exists()

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "GEO Strategy Report V2" in text
    assert "Leadership Summary" in text
    assert "Priority Findings" in text
    assert "Key Pages Are Not Ai-Citation Ready" in text
    assert "Competitive Benchmark" in text
    assert "30/60/90 Action Plan" in text
    assert "Proof Appendix" in text
