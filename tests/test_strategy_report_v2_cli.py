from scripts.strategy_report_v2 import parse_args


def test_strategy_report_v2_has_separate_entrypoint():
    args = parse_args(["https://www.transglobalus.com/"])
    assert args.url == "https://www.transglobalus.com/"
