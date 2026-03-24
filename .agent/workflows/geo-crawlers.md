---
description: Check which AI crawlers can access your website via robots.txt
---

# GEO Crawler Analysis Workflow

// turbo-all

Analyze robots.txt to check AI crawler access (GPTBot, ClaudeBot, PerplexityBot, etc.)

## Steps

1. **Fetch robots.txt analysis**:
   ```
   python scripts/fetch_page.py <URL> robots
   ```

2. **Interpret results** using `skills/geo-crawlers/SKILL.md`:
   - 14 AI crawlers checked: GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, PerplexityBot, Amazonbot, Google-Extended, Bytespider, CCBot, Applebot-Extended, FacebookBot, Cohere-ai, etc.
   - Statuses: ALLOWED, BLOCKED, PARTIALLY_BLOCKED, NOT_MENTIONED
   - Scoring: Start at 100, -15 per critical crawler blocked, -5 per secondary

3. **Provide specific recommendations**:
   - Which crawlers to allow/block and why
   - Recommended robots.txt additions
   - Crawl-delay considerations
