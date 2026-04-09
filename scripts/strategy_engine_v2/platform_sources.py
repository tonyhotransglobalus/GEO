from __future__ import annotations

from typing import Any


OFFICIAL_PLATFORM_SOURCES: list[dict[str, str]] = [
    {
        "platform": "google",
        "title": "Google Search AI features",
        "url": "https://developers.google.com/search/docs/appearance/ai-features",
        "category": "ai-search",
        "note": "Google Search Central guidance for AI features, AI Overviews, and AI Mode.",
    },
    {
        "platform": "openai",
        "title": "OpenAI Publishers and Developers FAQ",
        "url": "https://help.openai.com/en/articles/12627856-publishers-and-developers-faq",
        "category": "bots-and-search",
        "note": "Official OpenAI publisher guidance covering OAI-SearchBot, GPTBot, referrals, and controls.",
    },
    {
        "platform": "openai",
        "title": "OpenAI ChatGPT search overview",
        "url": "https://help.openai.com/en/articles/9237897-chatgpt-search",
        "category": "search-product",
        "note": "Product overview for ChatGPT search behavior and usage.",
    },
    {
        "platform": "anthropic",
        "title": "Anthropic crawler guidance",
        "url": "https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler",
        "category": "bots-and-search",
        "note": "Official Anthropic guidance for ClaudeBot, Claude-User, and Claude-SearchBot.",
    },
    {
        "platform": "perplexity",
        "title": "Perplexity crawler guidance",
        "url": "https://docs.perplexity.ai/docs/resources/perplexity-crawlers",
        "category": "bots-and-search",
        "note": "Official Perplexity bot, WAF, and IP guidance.",
    },
    {
        "platform": "bing",
        "title": "Bing AI Performance",
        "url": "https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview",
        "category": "measurement",
        "note": "Official Bing Webmaster Tools AI Performance announcement with citations and grounding queries.",
    },
    {
        "platform": "bing",
        "title": "Bing grounding on the AI web",
        "url": "https://blogs.bing.com/search/February-2026/Elevating-the-Role-of-Grounding-on-the-AI-Web",
        "category": "ai-search",
        "note": "Microsoft guidance on grounding, citations, and cited pages.",
    },
    {
        "platform": "llmstxt",
        "title": "llms.txt specification",
        "url": "https://llmstxt.org/core.html",
        "category": "optional-spec",
        "note": "Public llms.txt specification; useful as optional guidance, not a universal requirement.",
    },
]


_PLATFORM_ALIASES = {
    "chatgpt": "openai",
    "openai": "openai",
    "gpt": "openai",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "perplexity": "perplexity",
    "google": "google",
    "gemini": "google",
    "bing": "bing",
    "copilot": "bing",
    "llms.txt": "llmstxt",
    "llmstxt": "llmstxt",
}


def _normalized_platform(value: Any) -> str:
    return str(value or "").strip().lower()


def sources_for_platform(platform: Any) -> list[dict[str, str]]:
    alias = _PLATFORM_ALIASES.get(_normalized_platform(platform), _normalized_platform(platform))
    return [dict(item) for item in OFFICIAL_PLATFORM_SOURCES if item["platform"] == alias]


def default_official_sources() -> list[dict[str, str]]:
    seen: set[str] = set()
    ordered: list[dict[str, str]] = []
    for item in OFFICIAL_PLATFORM_SOURCES:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        ordered.append(dict(item))
    return ordered
