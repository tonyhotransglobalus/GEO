---
description: Quick 60-second GEO visibility snapshot of a website
---

# GEO Quick Audit Workflow

// turbo-all

Run a fast GEO visibility check on a website — takes ~60 seconds.

## Steps

1. **Fetch page data and robots.txt**:
   ```
   python scripts/fetch_page.py <URL> full
   ```

2. **Run citability scoring**:
   ```
   python scripts/citability_scorer.py <URL>
   ```

3. **Summarize findings** in a quick inline format:
   - Overall estimated GEO score (0-100)
   - AI Crawler access (allowed/blocked for top crawlers)
   - Top 3 most citable passages
   - llms.txt presence (yes/no)
   - Key schema types found
   - 3 quick wins

Reference `skills/geo-audit/SKILL.md` for scoring methodology.
